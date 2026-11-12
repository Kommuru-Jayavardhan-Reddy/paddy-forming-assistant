"""
Paddy Farming Assistant - SQLAlchemy 2.x Async Tenant Session Manager
Manages tenant-specific database connections and sessions with database-enforced identity.
Guarantees transaction-scoped isolation, connection pool safety, encrypted credential handling,
and verified database identity.
"""

import logging
from typing import AsyncGenerator, Dict, Optional
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app import config
from app.core.crypto import decrypt_tenant_secret, CredentialEncryptionError
from app.services.tenant_provisioning import validate_tenant_schema_name

logger = logging.getLogger(__name__)

# Cache of tenant async engines to manage connection pooling per active tenant
_tenant_engines: Dict[str, AsyncEngine] = {}


class TenantSecurityError(Exception):
    """Raised when tenant database identity or authorization fails."""
    pass


def get_tenant_database_url(
    schema_name: str,
    raw_secret: str,
    target_database: Optional[str] = None
) -> URL:
    """
    Constructs the SQLAlchemy connection URL safely for the tenant's specific database identity.
    Uses 'tenant_<schema_name>' as the database user.
    """
    valid_schema = validate_tenant_schema_name(schema_name)
    role_name = f"tenant_{valid_schema}"

    return URL.create(
        drivername="postgresql+asyncpg",
        username=role_name,
        password=raw_secret,
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=target_database or config.POSTGRES_DB,
    )


def get_or_create_tenant_engine(
    schema_name: str,
    raw_secret: str,
    target_database: Optional[str] = None
) -> AsyncEngine:
    """
    Returns an AsyncEngine initialized with the tenant's dedicated database identity.
    Reuses existing engine from cache if present.
    """
    valid_schema = validate_tenant_schema_name(schema_name)
    engine_key = f"{valid_schema}:{target_database or config.POSTGRES_DB}"

    if engine_key not in _tenant_engines:
        db_url = get_tenant_database_url(valid_schema, raw_secret, target_database)
        engine = create_async_engine(
            db_url,
            pool_size=2,
            max_overflow=3,
            pool_timeout=10,
            pool_pre_ping=True,
            echo=False,
            future=True,
        )
        _tenant_engines[engine_key] = engine

    return _tenant_engines[engine_key]


async def evict_tenant_engine(schema_name: str):
    """Disposes and removes cached engines for a tenant (used upon credential rotation)."""
    valid_schema = validate_tenant_schema_name(schema_name)
    for key in list(_tenant_engines.keys()):
        if key.startswith(f"{valid_schema}:"):
            engine = _tenant_engines.pop(key, None)
            if engine is not None:
                try:
                    await engine.dispose()
                except Exception as exc:
                    logger.warning("Error disposing tenant engine %s during eviction: %s", key, exc)


async def close_all_tenant_engines():
    """Disposes of all cached tenant engines during application shutdown."""
    for key, engine in list(_tenant_engines.items()):
        try:
            await engine.dispose()
        except Exception as exc:
            logger.warning("Error disposing tenant engine %s: %s", key, exc)
    _tenant_engines.clear()


@asynccontextmanager
async def tenant_session_scope(
    schema_name: str,
    encrypted_db_secret: str,
    target_database: Optional[str] = None,
    raw_secret_override: Optional[str] = None
) -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous context manager providing a safe, isolated database session.
    
    Security Guarantees:
    1. Decrypts authenticated ciphertext in memory; never logs or stores plaintext.
    2. Connects using the tenant's isolated database identity 'tenant_<schema_name>'.
    3. Opens an explicit transaction block with session.begin().
    4. Sets transaction-local search path: 'SET LOCAL search_path TO "<schema_name>", public;'.
    5. Verifies current_user == 'tenant_<schema_name>' before executing any application logic.
    6. Automatically rolls back on any error and closes session safely.
    """
    valid_schema = validate_tenant_schema_name(schema_name)
    expected_role = f"tenant_{valid_schema}"

    # Decrypt credential in-memory
    if raw_secret_override:
        raw_secret = raw_secret_override
    else:
        try:
            raw_secret = decrypt_tenant_secret(encrypted_db_secret)
        except CredentialEncryptionError as exc:
            raise TenantSecurityError("Unable to decrypt tenant database credential.") from exc

    engine = get_or_create_tenant_engine(valid_schema, raw_secret, target_database)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        try:
            async with session.begin():
                # 1. Set transaction-local search path (safely quoted identifier)
                await session.execute(text(f'SET LOCAL search_path TO "{valid_schema}", public;'))

                # 2. Strict verification of database identity and schema
                res = await session.execute(text("SELECT current_user, current_schema();"))
                curr_user, curr_schema = res.one()

                if curr_user != expected_role:
                    raise TenantSecurityError(
                        f"Database identity mismatch! Expected role '{expected_role}', but connected as '{curr_user}'."
                    )

                if curr_schema != valid_schema:
                    raise TenantSecurityError(
                        f"Schema resolution failure! Expected '{valid_schema}', but got '{curr_schema}'."
                    )

                yield session

        except Exception as exc:
            logger.error("Tenant session failure for schema '%s': %s", valid_schema, exc)
            raise
        finally:
            await session.close()
