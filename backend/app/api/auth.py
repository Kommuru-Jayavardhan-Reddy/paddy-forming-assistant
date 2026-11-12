"""
Paddy Farming Assistant - Authentication & Administrative API Router
Implements secure public farmer registration, authentication, profile inspection,
and strictly isolated administrative provisioning.
Guarantees:
- Client cannot escalate privileges during registration (role is server-enforced 'farmer').
- Admin APIs require verified server-side 'admin' role claims derived from authentic database records.
- Argon2id password hashing and PyJWT HS256 token issuance.
"""

import os
import uuid
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import asyncpg

from app import config
from app.exceptions import SecurityConfigurationError
from app.core.security import hash_password, verify_password, create_access_token
from app.core.phone import normalize_mobile_number, validate_indian_mobile_number, InvalidMobileNumberError
from app.core.crypto import encrypt_tenant_secret
from app.core.dependencies import get_current_user, require_admin
from app.db.session import get_db
from app.db.models.farmer import Farmer, UserRole
from app.db.models.password_reset import PasswordResetOTP
from app.schemas.auth import (
    FarmerRegisterRequest,
    FarmerLoginRequest,
    AuthTokenResponse,
    FarmerProfileResponse,
    AdminCreateRequest,
    AdminPromoteRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
    ResendOTPRequest,
    ResendOTPResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.services.sms_service import sms_service, SMSDeliveryError, mask_phone_number
from app.services.tenant_provisioning import (
    generate_tenant_schema_name,
    generate_tenant_db_secret,
    provision_tenant_database_objects,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Authentication & Administration"])


async def _get_privileged_conn(target_db: str) -> asyncpg.Connection:
    """
    Acquires a privileged database connection for tenant provisioning.
    Strictly requires POSTGRES_PASSWORD in environment. Fallback passwords are forbidden.
    """
    pwd = os.getenv("POSTGRES_PASSWORD")
    if not pwd or not pwd.strip():
        logger.critical("Privileged database connection blocked: POSTGRES_PASSWORD is not configured.")
        raise SecurityConfigurationError(
            "Privileged database operations cannot proceed: POSTGRES_PASSWORD is not configured."
        )
    return await asyncpg.connect(
        user="postgres",
        password=pwd.strip(),
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=target_db,
    )


@router.post(
    "/auth/register",
    response_model=FarmerProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public Farmer Registration",
)
async def register_farmer(
    request: FarmerRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Registers a new agricultural producer.
    Security rules enforced:
    1. Unconditionally assigns role='farmer'. Any client-supplied 'role' or 'is_admin' field is discarded.
    2. Hashes password using Argon2id.
    3. Normalizes and validates E.164 mobile number if provided.
    4. Provisions dedicated isolated PostgreSQL schema and tenant database role.
    """
    # 1. Check if username is already taken
    existing_user = await db.execute(select(Farmer).where(Farmer.username == request.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' is already registered.",
        )

    # 2. Validate mandatory Full Name
    if not request.full_name or not request.full_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name is required and cannot be empty or whitespace only.",
        )

    # 3. Validate mandatory Indian Mobile Number and check uniqueness
    if not request.mobile_number or not request.mobile_number.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile number is required and cannot be empty.",
        )

    try:
        norm_mobile = validate_indian_mobile_number(request.mobile_number)
    except InvalidMobileNumberError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid mobile number: {exc}",
        )
    existing_mobile = await db.execute(select(Farmer).where(Farmer.normalized_mobile == norm_mobile))
    if existing_mobile.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This mobile number is already registered to another account.",
        )

    # 3. Hash password using Argon2id
    pwd_hash = hash_password(request.password)

    # 4. Strictly enforce role='farmer' on server
    assigned_role = UserRole.FARMER.value

    # 5. Generate tenant schema name and credentials
    farmer_id = uuid.uuid4()
    schema_name = generate_tenant_schema_name()
    raw_secret = generate_tenant_db_secret()
    encrypted_secret = encrypt_tenant_secret(raw_secret)

    # 6. Provision isolated PostgreSQL schema & role
    # Determine active database from session bind
    target_db = config.POSTGRES_DB
    try:
        bind_url = db.bind.url
        if bind_url and bind_url.database:
            target_db = bind_url.database
    except Exception:
        pass

    try:
        priv_conn = await _get_privileged_conn(target_db)
        try:
            await provision_tenant_database_objects(
                conn=priv_conn,
                farmer_id=farmer_id,
                schema_name=schema_name,
                database_name=target_db,
                raw_secret_override=raw_secret,
            )
        finally:
            await priv_conn.close()
    except Exception as exc:
        logger.error("Failed to provision tenant database objects: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize tenant database workspace. Please try again.",
        )

    # 7. Persist Farmer master record
    new_farmer = Farmer(
        id=farmer_id,
        username=request.username,
        password_hash=pwd_hash,
        mobile_number=request.mobile_number,
        normalized_mobile=norm_mobile,
        role=assigned_role,
        schema_name=schema_name,
        encrypted_db_secret=encrypted_secret,
        full_name=request.full_name,
        farm_name=request.farm_name,
        village=request.village,
        is_active=True,
    )
    db.add(new_farmer)
    await db.commit()
    await db.refresh(new_farmer)

    logger.info("Farmer '%s' successfully registered with schema '%s' (role='%s').", new_farmer.username, schema_name, assigned_role)
    return new_farmer


@router.post(
    "/auth/login",
    response_model=AuthTokenResponse,
    summary="User & Administrator Login",
)
async def login(
    request: FarmerLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates a farmer or administrator using Argon2id password verification.
    Supports authenticating via username OR registered mobile number (Indian 10-digit or E.164).
    Issues a cryptographically signed HS256 access token with verified database claims.
    """
    identifier = request.get_identifier()

    # 1. Attempt lookup by exact username first (preserves backward compatibility and legacy accounts)
    result = await db.execute(select(Farmer).where(Farmer.username == identifier))
    farmer = result.scalar_one_or_none()

    # 2. If not found by username, attempt lookup by normalized E.164 mobile number
    if not farmer:
        try:
            norm_mobile = normalize_mobile_number(identifier)
            mobile_result = await db.execute(select(Farmer).where(Farmer.normalized_mobile == norm_mobile))
            farmer = mobile_result.scalar_one_or_none()
        except InvalidMobileNumberError:
            farmer = None

    if not farmer or not verify_password(request.password, farmer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username, mobile number, or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not farmer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    # Embed verified database claims into access token
    token_claims = {
        "sub": str(farmer.id),
        "username": farmer.username,
        "role": farmer.role,
        "schema_name": farmer.schema_name,
    }
    token = create_access_token(data=token_claims)

    return AuthTokenResponse(
        access_token=token,
        token_type="access",
        role=farmer.role,
        username=farmer.username,
        farmer_id=str(farmer.id),
        schema_name=farmer.schema_name,
    )


@router.get(
    "/auth/me",
    response_model=FarmerProfileResponse,
    summary="Get Current User Profile",
)
async def get_current_profile(
    current_user: Farmer = Depends(get_current_user),
):
    """Retrieves profile of the authenticated user based on verified Bearer token."""
    return current_user


# ==============================================================================
# Protected Administrative Endpoints (Admin Role Required Server-Side)
# ==============================================================================

@router.post(
    "/admin/provision",
    response_model=FarmerProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision New Administrator Account (Admin-Only)",
)
async def provision_admin(
    request: AdminCreateRequest,
    current_admin: Farmer = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Trusted administrative provisioning of an Admin account.
    Strictly protected: can only be invoked by an authenticated administrator.
    Admin accounts have role='admin' and schema_name=NULL (no tenant schema).
    """
    existing_user = await db.execute(select(Farmer).where(Farmer.username == request.username))
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' is already in use.",
        )

    admin_farmer = Farmer(
        id=uuid.uuid4(),
        username=request.username,
        password_hash=hash_password(request.password),
        mobile_number=None,
        normalized_mobile=None,
        role=UserRole.ADMIN.value,
        schema_name=None,
        encrypted_db_secret=None,
        full_name=request.full_name,
        farm_name=None,
        village=None,
        is_active=True,
    )
    db.add(admin_farmer)
    await db.commit()
    await db.refresh(admin_farmer)

    logger.info("Admin account '%s' provisioned by '%s'.", admin_farmer.username, current_admin.username)
    return admin_farmer


@router.post(
    "/admin/promote",
    response_model=FarmerProfileResponse,
    summary="Promote Farmer to Administrator (Admin-Only)",
)
async def promote_to_admin(
    request: AdminPromoteRequest,
    current_admin: Farmer = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Promotes an existing farmer to Admin role.
    Strictly protected: can only be performed by an authenticated administrator.
    """
    result = await db.execute(select(Farmer).where(Farmer.username == request.target_username))
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{request.target_username}' not found.",
        )

    target.role = UserRole.ADMIN.value
    # Admin accounts do not have tenant schemas per CheckConstraint
    target.schema_name = None
    target.encrypted_db_secret = None

    await db.commit()
    await db.refresh(target)

    logger.info("User '%s' promoted to Administrator by '%s'.", target.username, current_admin.username)
    return target


@router.get(
    "/admin/system-status",
    summary="System Diagnostic Information (Admin-Only)",
)
async def get_system_status(
    current_admin: Farmer = Depends(require_admin),
):
    """
    Protected diagnostic endpoint.
    Strictly requires server-side verified Admin privileges.
    """
    return {
        "status": "operational",
        "authenticated_admin": current_admin.username,
        "role": current_admin.role,
        "access_granted": True,
    }


# ==============================================================================
# Forgot Password & Secure OTP Endpoints
# ==============================================================================

@router.post(
    "/auth/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request Password Reset OTP",
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1 & 2: Initiates password reset for a registered farmer.
    1. Validates and normalizes mobile number to E.164.
    2. Verifies registration against existing farmers database.
    3. Generates secure random 6-digit OTP and hashes it with Argon2id.
    4. Dispatches OTP via configured SMS service (real gateway in production, simulation in dev).
    5. Enforces single active session per mobile number.
    """
    try:
        norm_mobile = validate_indian_mobile_number(request.mobile_number)
    except InvalidMobileNumberError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid mobile number format: {exc}",
        )

    # Verify farmer exists with this normalized mobile number
    result = await db.execute(select(Farmer).where(Farmer.normalized_mobile == norm_mobile))
    farmer = result.scalar_one_or_none()

    if not farmer:
        logger.warning("Password reset requested for unregistered mobile: %s", mask_phone_number(norm_mobile))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This mobile number is not registered with any farmer account. Please check your number or register.",
        )

    if not farmer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is deactivated. Please contact support.",
        )

    # Invalidate any prior active or pending OTPs for this mobile
    await db.execute(
        update(PasswordResetOTP)
        .where(
            PasswordResetOTP.normalized_mobile == norm_mobile,
            PasswordResetOTP.is_used == False,
        )
        .values(is_used=True)
    )

    # Generate secure 6-digit OTP (100000 - 999999)
    raw_otp = f"{secrets.randbelow(900000) + 100000}"
    hashed_otp = hash_password(raw_otp)

    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=5)

    otp_record = PasswordResetOTP(
        id=session_id,
        farmer_id=farmer.id,
        mobile_number=request.mobile_number,
        normalized_mobile=norm_mobile,
        otp_hash=hashed_otp,
        reset_token_hash=None,
        attempts=0,
        max_attempts=5,
        is_verified=False,
        is_used=False,
        expires_at=expires_at,
        last_resend_at=now,
        created_at=now,
    )
    db.add(otp_record)
    await db.commit()

    # Dispatch OTP via SMS Service
    try:
        dispatch_result = await sms_service.send_otp(norm_mobile, raw_otp)
    except SMSDeliveryError as exc:
        logger.error("SMS dispatch failure for %s: %s", mask_phone_number(norm_mobile), exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SMS delivery failed: {exc}",
        )

    logger.info("Password reset OTP generated and dispatched to %s (Session ID: %s).", mask_phone_number(norm_mobile), session_id)

    return ForgotPasswordResponse(
        success=True,
        message="Verification code sent to your registered mobile number.",
        session_id=str(session_id),
        masked_mobile=mask_phone_number(norm_mobile),
        expires_in_seconds=300,
        cooldown_seconds=60,
        dev_otp=dispatch_result.dev_otp if not sms_service.is_production else None,
    )


@router.post(
    "/auth/resend-otp",
    response_model=ResendOTPResponse,
    summary="Resend Password Reset OTP",
)
async def resend_otp(
    request: ResendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3 (Resend): Resends verification OTP enforcing a 60-second cooldown period.
    Generates a new secure 6-digit OTP, updates expiration, and resets attempt counter.
    """
    try:
        sess_uuid = uuid.UUID(request.session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session identifier format.",
        )

    res = await db.execute(select(PasswordResetOTP).where(PasswordResetOTP.id == sess_uuid))
    otp_record = res.scalar_one_or_none()

    if not otp_record or otp_record.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset session not found or has already been completed. Please start over.",
        )

    # Enforce 60-second cooldown
    now = datetime.now(timezone.utc)
    elapsed = (now - otp_record.last_resend_at).total_seconds()
    if elapsed < 60:
        remaining = int(60 - elapsed)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining} seconds before requesting a new OTP.",
        )

    # Generate fresh 6-digit OTP
    fresh_otp = f"{secrets.randbelow(900000) + 100000}"
    otp_record.otp_hash = hash_password(fresh_otp)
    otp_record.attempts = 0  # Reset incorrect attempt counter for the fresh OTP
    otp_record.expires_at = now + timedelta(minutes=5)
    otp_record.last_resend_at = now
    await db.commit()

    try:
        dispatch_result = await sms_service.send_otp(otp_record.normalized_mobile, fresh_otp)
    except SMSDeliveryError as exc:
        logger.error("SMS resend failure for %s: %s", mask_phone_number(otp_record.normalized_mobile), exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SMS delivery failed: {exc}",
        )

    logger.info("Fresh OTP resent for session %s (Recipient: %s).", sess_uuid, mask_phone_number(otp_record.normalized_mobile))

    return ResendOTPResponse(
        success=True,
        message="A fresh verification code has been sent to your mobile number.",
        session_id=str(sess_uuid),
        expires_in_seconds=300,
        cooldown_seconds=60,
        dev_otp=dispatch_result.dev_otp if not sms_service.is_production else None,
    )


@router.post(
    "/auth/verify-otp",
    response_model=VerifyOTPResponse,
    summary="Verify Password Reset OTP",
)
async def verify_otp(
    request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3 (Verification): Validates entered OTP against stored hash.
    - Rejects expired OTPs (> 5 minutes).
    - Enforces maximum 5 attempts to protect against brute-force attacks.
    - Issues cryptographically signed single-use reset authorization token.
    """
    try:
        sess_uuid = uuid.UUID(request.session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session identifier format.",
        )

    res = await db.execute(select(PasswordResetOTP).where(PasswordResetOTP.id == sess_uuid))
    otp_record = res.scalar_one_or_none()

    if not otp_record or otp_record.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset session not found or has already been completed.",
        )

    now = datetime.now(timezone.utc)
    if now > otp_record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired (validity is 5 minutes). Please request a new code.",
        )

    if otp_record.attempts >= otp_record.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum verification attempts exceeded. This session is locked. Please request a new code.",
        )

    # Verify entered OTP
    is_valid = verify_password(request.otp, otp_record.otp_hash)

    if not is_valid:
        otp_record.attempts += 1
        await db.commit()
        remaining = max(0, otp_record.max_attempts - otp_record.attempts)
        if remaining == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many incorrect OTP attempts. This session is locked. Please request a new code.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect verification code. {remaining} attempt(s) remaining.",
        )

    # OTP is valid: generate single-use reset authorization token
    reset_token = secrets.token_urlsafe(48)
    otp_record.is_verified = True
    otp_record.reset_token_hash = hash_password(reset_token)
    await db.commit()

    logger.info("OTP successfully verified for session %s (Recipient: %s).", sess_uuid, mask_phone_number(otp_record.normalized_mobile))

    return VerifyOTPResponse(
        success=True,
        message="Mobile number verified successfully.",
        reset_token=reset_token,
    )


@router.post(
    "/auth/reset-password",
    response_model=ResetPasswordResponse,
    summary="Complete Password Reset",
)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 4 & 5: Sets new password using verified reset token.
    1. Validates password strength and match.
    2. Verifies single-use reset authorization token against active verified sessions.
    3. Hashes new password using Argon2id with OWASP parameters.
    4. Updates farmer record in PostgreSQL database.
    5. Immediately invalidates reset token and OTP session (single use).
    """
    # Find active verified session matching reset token
    res = await db.execute(
        select(PasswordResetOTP).where(
            PasswordResetOTP.is_verified == True,
            PasswordResetOTP.is_used == False,
            PasswordResetOTP.reset_token_hash != None,
        )
    )
    candidates = res.scalars().all()

    matched_session: Optional[PasswordResetOTP] = None
    for sess in candidates:
        if sess.reset_token_hash and verify_password(request.reset_token, sess.reset_token_hash):
            matched_session = sess
            break

    if not matched_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired password reset token. Please initiate a new password reset.",
        )

    # Verify session window (must complete reset within 15 minutes of initiation)
    now = datetime.now(timezone.utc)
    if (now - matched_session.created_at).total_seconds() > 900:
        matched_session.is_used = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset session has expired (15-minute window exceeded). Please start over.",
        )

    # Retrieve Farmer record
    farmer_res = await db.execute(select(Farmer).where(Farmer.id == matched_session.farmer_id))
    farmer = farmer_res.scalar_one_or_none()

    if not farmer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated farmer account was not found.",
        )

    # Hash new password with Argon2id
    farmer.password_hash = hash_password(request.new_password)
    farmer.updated_at = now

    # Invalidate current session (single use)
    matched_session.is_used = True
    matched_session.reset_token_hash = None

    # Invalidate any other outstanding reset sessions for this farmer
    await db.execute(
        update(PasswordResetOTP)
        .where(
            PasswordResetOTP.farmer_id == farmer.id,
            PasswordResetOTP.is_used == False,
        )
        .values(is_used=True)
    )

    await db.commit()

    logger.info("Password successfully updated for farmer '%s'.", farmer.username)

    return ResetPasswordResponse(
        success=True,
        message="Password updated successfully! You can now sign in with your new password.",
    )

