"""
Paddy Farming Assistant - Authentication & Authorization Pydantic Schemas
Defines request and response schemas for farmer registration, login, and administrative management.
Strictly prevents privilege escalation by ensuring client input cannot set security roles.
"""

from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class FarmerRegisterRequest(BaseModel):
    """
    Public registration request model.
    Any attempt by a client to submit 'role', 'is_admin', or other privilege fields
    is strictly ignored by the model configuration and server business logic.
    Mobile number and full name are strictly mandatory for all new farmer registrations.
    """
    username: str = Field(..., min_length=3, max_length=100, description="Farmer login handle")
    password: str = Field(..., min_length=8, max_length=128, description="Farmer plaintext password (hashed with Argon2id)")
    mobile_number: str = Field(..., min_length=10, max_length=25, description="Contact mobile number")
    full_name: str = Field(..., min_length=1, max_length=150, description="Farmer full name")
    farm_name: Optional[str] = Field(None, max_length=150, description="Agricultural holding name")
    village: Optional[str] = Field(None, max_length=100, description="Village or locality")

    # Extra fields sent by clients (e.g. role='admin', is_admin=True) are ignored and never trusted
    model_config = ConfigDict(extra="ignore")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        clean = v.strip() if isinstance(v, str) else ""
        if not clean:
            raise ValueError("Farmer username cannot be empty or blank.")
        return clean

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        clean = v.strip() if isinstance(v, str) else ""
        if not clean:
            raise ValueError("Full name cannot be empty or whitespace only.")
        return clean

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v: str) -> str:
        clean = v.strip() if isinstance(v, str) else ""
        if not clean:
            raise ValueError("Mobile number cannot be empty or whitespace only.")
        return clean


class FarmerLoginRequest(BaseModel):
    """
    Farmer and Administrator login request payload.
    Supports authenticating via username or registered mobile number (Indian 10-digit or E.164).
    """
    username: Optional[str] = Field(None, min_length=1, max_length=100, description="Account username or registered mobile number")
    mobile_number: Optional[str] = Field(None, min_length=1, max_length=30, description="Optional explicit mobile number")
    password: str = Field(..., min_length=1, max_length=128, description="Account password")

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def validate_identifier_present(self) -> "FarmerLoginRequest":
        ident = (self.mobile_number or self.username or "").strip()
        if not ident:
            raise ValueError("Either 'username' or 'mobile_number' must be provided.")
        return self

    def get_identifier(self) -> str:
        """Returns the trimmed login identifier (mobile_number prioritized if supplied, else username)."""
        return (self.mobile_number or self.username or "").strip()


class AuthTokenResponse(BaseModel):
    """JWT authentication token response with verified identity claims."""
    access_token: str = Field(..., description="Signed HS256 JWT access token")
    token_type: str = Field(default="access", description="Token type claim")
    role: str = Field(..., description="Verified database role: 'farmer' or 'admin'")
    username: str = Field(..., description="Authenticated username")
    farmer_id: str = Field(..., description="Surrogate UUID string of the authenticated user")
    schema_name: Optional[str] = Field(None, description="Dedicated tenant PostgreSQL schema (NULL for admin)")


class FarmerProfileResponse(BaseModel):
    """Safe farmer profile response excluding password hashes and database secrets."""
    id: uuid.UUID
    username: str
    mobile_number: Optional[str] = None
    normalized_mobile: Optional[str] = None
    role: str
    schema_name: Optional[str] = None
    full_name: Optional[str] = None
    farm_name: Optional[str] = None
    village: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminCreateRequest(BaseModel):
    """Request model for trusted administrative provisioning of an Admin account."""
    username: str = Field(..., min_length=3, max_length=100, description="Admin username")
    password: str = Field(..., min_length=8, max_length=128, description="Admin password")
    full_name: Optional[str] = Field(None, max_length=150, description="Admin full name")


class AdminPromoteRequest(BaseModel):
    """Request model to promote an existing farmer to Admin role (Admin-only)."""
    target_username: str = Field(..., min_length=3, max_length=100, description="Username of the farmer to promote")


# ==============================================================================
# Forgot Password & Secure OTP Schemas
# ==============================================================================

class ForgotPasswordRequest(BaseModel):
    """Request payload to initiate forgot password and request an OTP."""
    mobile_number: str = Field(
        ...,
        min_length=10,
        max_length=25,
        description="Farmer's registered 10-digit Indian or international E.164 mobile number",
    )

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        clean = v.strip() if isinstance(v, str) else ""
        if not clean:
            raise ValueError("Mobile number is required and cannot be empty.")
        return clean


class ForgotPasswordResponse(BaseModel):
    """Response payload returned when an OTP is dispatched."""
    success: bool = True
    message: str
    session_id: str
    masked_mobile: Optional[str] = None
    expires_in_seconds: int = 300
    cooldown_seconds: int = 60
    dev_otp: Optional[str] = None


class VerifyOTPRequest(BaseModel):
    """Request payload to verify the 6-digit OTP."""
    session_id: str = Field(..., description="UUID session identifier returned from /forgot-password")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        clean = v.strip() if isinstance(v, str) else ""
        if not clean or not clean.isdigit() or len(clean) != 6:
            raise ValueError("OTP must be exactly 6 numeric digits.")
        return clean


class VerifyOTPResponse(BaseModel):
    """Response payload returned upon successful OTP verification."""
    success: bool = True
    message: str
    reset_token: str = Field(..., description="Single-use authorization token required to reset password")


class ResendOTPRequest(BaseModel):
    """Request payload to resend an OTP under the 60-second cooldown rule."""
    session_id: str = Field(..., description="UUID session identifier returned from /forgot-password")


class ResendOTPResponse(BaseModel):
    """Response payload returned when an OTP is resent."""
    success: bool = True
    message: str
    session_id: str
    expires_in_seconds: int = 300
    cooldown_seconds: int = 60
    dev_otp: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    """Request payload to update the password with verified reset token."""
    reset_token: str = Field(..., min_length=16, description="Verified single-use reset authorization token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New strong password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirmation matching new password")

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, one lowercase letter, and one number."
            )
        return v

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match.")
        return self


class ResetPasswordResponse(BaseModel):
    """Response payload confirming password was updated."""
    success: bool = True
    message: str


