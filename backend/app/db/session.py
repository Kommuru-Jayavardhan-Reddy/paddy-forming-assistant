"""
Paddy Farming Assistant - Async SQLAlchemy Database Session Management (STEP 11F.3)
Manages asynchronous database connection pooling, AsyncSession lifecycle,
and non-destructive connectivity verification using SQLAlchemy 2.x and asyncpg.
"""

import time
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app import config

logger = logging.getLogger(__name__)

# Module-level engine and session factory singletons
_async_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> URL:
    """
    Constructs the SQLAlchemy connection URL safely using URL.create().
    Guarantees special characters in passwords do not break parsing.
    Never exposes or logs the constructed URL with credentials.
    """
    return URL.create(
        drivername="postgresql+asyncpg",
        username=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=config.POSTGRES_DB,
    )


def init_db_engine() -> AsyncEngine:
    """
    Initializes the asynchronous SQLAlchemy engine with safe connection pooling defaults.
    Reuses existing engine if already initialized.
    """
    global _async_engine, _async_session_factory

    if _async_engine is not None:
        return _async_engine

    db_url = get_database_url()

    logger.info(
        "Initializing SQLAlchemy async engine for database '%s' at %s:%s (pool_size=%d, max_overflow=%d)...",
        config.POSTGRES_DB,
        config.POSTGRES_HOST,
        config.POSTGRES_PORT,
        config.DB_POOL_SIZE,
        config.DB_MAX_OVERFLOW,
    )

    _async_engine = create_async_engine(
        db_url,
        pool_size=config.DB_POOL_SIZE,
        max_overflow=config.DB_MAX_OVERFLOW,
        pool_timeout=config.DB_POOL_TIMEOUT,
        pool_pre_ping=config.DB_POOL_PRE_PING,
        echo=config.DB_ECHO,
        future=True,
    )

    _async_session_factory = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    return _async_engine


def get_async_engine() -> AsyncEngine:
    """
    Returns the active AsyncEngine singleton, initializing it if necessary.
    """
    if _async_engine is None:
        return init_db_engine()
    return _async_engine


async def close_db_engine():
    """
    Disposes of the AsyncEngine connection pool cleanly during application shutdown.
    """
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        logger.info("Disposing SQLAlchemy async engine connection pool...")
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("SQLAlchemy async engine disposed cleanly.")


def AsyncSessionLocal() -> AsyncSession:
    """
    Creates a new standalone AsyncSession instance from the active sessionmaker.
    """
    if _async_session_factory is None:
        init_db_engine()
    return _async_session_factory()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding a managed AsyncSession per request.
    Guarantees session rollback on unhandled exceptions and proper cleanup.
    """
    if _async_session_factory is None:
        init_db_engine()

    async with _async_session_factory() as session:
        try:
            yield session
        except Exception as exc:
            await session.rollback()
            logger.error("Database session rolled back due to error: %s", exc)
            raise
        finally:
            await session.close()


async def check_db_connectivity() -> Dict[str, Any]:
    """
    Performs a non-destructive database health check by executing 'SELECT 1'.
    Confirms connection, current database name, active user, and query latency.
    Categorizes errors without exposing credentials, passwords, or internal secrets.
    """
    if not config.POSTGRES_PASSWORD:
        return {
            "status": "unhealthy",
            "connected": False,
            "error_type": "configuration_error",
            "detail": "Database password is not configured in backend environment.",
            "database": config.POSTGRES_DB,
            "host": config.POSTGRES_HOST,
            "port": config.POSTGRES_PORT,
        }

    engine = get_async_engine()
    start_time = time.perf_counter()

    try:
        async with engine.connect() as conn:
            query = text("SELECT 1 AS alive, current_database() AS dbname, current_user AS username, inet_server_addr() AS srv_ip;")
            result = await conn.execute(query)
            row = result.mappings().one()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return {
                "status": "healthy",
                "connected": True,
                "database": row["dbname"],
                "user": row["username"],
                "host": config.POSTGRES_HOST,
                "port": config.POSTGRES_PORT,
                "latency_ms": latency_ms,
            }

    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        exc_str = str(exc).lower()

        if "password authentication failed" in exc_str or "invalidpassword" in exc_str or "28p01" in exc_str:
            err_type = "authentication_failure"
            detail = "Database authentication failed: invalid credentials."
        elif "connection refused" in exc_str or "could not connect" in exc_str or "oserror" in exc_str:
            err_type = "connection_failure"
            detail = f"Could not establish TCP connection to PostgreSQL server at {config.POSTGRES_HOST}:{config.POSTGRES_PORT}."
        elif "does not exist" in exc_str or "3d000" in exc_str:
            err_type = "database_not_found"
            detail = f"Target database '{config.POSTGRES_DB}' was not found on server."
        else:
            err_type = "operational_error"
            detail = "An operational error occurred while querying the database."

        logger.warning("Database connectivity check failed [%s]: %s", err_type, detail)
        return {
            "status": "unhealthy",
            "connected": False,
            "error_type": err_type,
            "detail": detail,
            "database": config.POSTGRES_DB,
            "host": config.POSTGRES_HOST,
            "port": config.POSTGRES_PORT,
            "latency_ms": latency_ms,
        }
