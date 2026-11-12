"""
Paddy Farming Assistant - Security & Authorization FastAPI Dependencies
Provides server-side identity verification, role-based access control, and token parsing.
Guarantees that privilege checks are verified against authentic database records.
"""

import uuid
import logging
from typing import Optional, AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.db.tenant_session import tenant_session_scope, TenantSecurityError
from app.db.models.farmer import Farmer
from app.exceptions import InvalidTokenError, TokenExpiredError

logger = logging.getLogger(__name__)

# Bearer token extractor
http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> Farmer:
    """
    Extracts and validates the JWT Bearer token from the Authorization header.
    Resolves the principal from the PostgreSQL master database and verifies active status.
    
    Raises:
        HTTPException 401: If token is missing, invalid, expired, or user not found/inactive.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.error("Unexpected error decoding access token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: missing subject identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token subject identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Resolve authentic user record from PostgreSQL
    result = await db.execute(select(Farmer).where(Farmer.id == user_uuid))
    farmer = result.scalar_one_or_none()

    if not farmer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user identity not found in database.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not farmer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact support.",
        )

    return farmer


async def require_admin(
    current_user: Farmer = Depends(get_current_user),
) -> Farmer:
    """
    Server-side role verification dependency: strictly requires 'admin' role.
    Rejects any request by non-admin users with HTTP 403 Forbidden.
    """
    if current_user.role != "admin":
        logger.warning(
            "Access denied: User '%s' (role='%s') attempted to access Admin endpoint.",
            current_user.username, current_user.role
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to perform this action.",
        )
    return current_user


async def require_farmer(
    current_user: Farmer = Depends(get_current_user),
) -> Farmer:
    """
    Server-side role verification dependency: requires 'farmer' or 'admin' role.
    """
    if current_user.role not in ("farmer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farmer or Administrator account required.",
        )
    return current_user


async def get_tenant_db(
    current_user: Farmer = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that resolves and yields an isolated, tenant-scoped SQLAlchemy AsyncSession.
    
    Security Guarantees:
    1. Authenticates caller via JWT Bearer token and verifies identity against PostgreSQL master.
    2. Validates that the farmer account has an initialized tenant schema and encrypted database secret.
    3. Restricts tenant database workspaces strictly to verified 'farmer' accounts.
    4. Connects via dedicated tenant database role 'tenant_<schema>' (least privilege).
    5. Sets transaction-local search path strictly to '<schema>', public.
    6. Ensures proper session teardown, automatic rollback on exceptions, and connection closure.
    """
    if current_user.role != "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant database workspace operations are restricted to verified farmer accounts.",
        )

    if not current_user.schema_name or not current_user.encrypted_db_secret:
        logger.error(
            "Access blocked: Farmer '%s' (id=%s) has no provisioned tenant workspace.",
            current_user.username, current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Farmer account has not been provisioned with a dedicated tenant workspace.",
        )

    try:
        async with tenant_session_scope(
            schema_name=current_user.schema_name,
            encrypted_db_secret=current_user.encrypted_db_secret,
        ) as session:
            yield session
    except TenantSecurityError as exc:
        logger.error("Tenant database security error for user '%s': %s", current_user.username, exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to establish secure tenant database connection.",
        )


__all__ = [
    "http_bearer",
    "get_current_user",
    "require_admin",
    "require_farmer",
    "get_tenant_db",
]

