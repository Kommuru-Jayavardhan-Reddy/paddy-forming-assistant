"""
Paddy Farming Assistant - Password Reset OTP & Token ORM Model
Maintains cryptographically hashed OTP records and password reset authorization tokens
with strict single-use invalidation, attempt limits, and expiration tracking.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Integer, func, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PasswordResetOTP(Base):
    """
    Password Reset OTP record representing an active or completed password reset session.
    Never stores plaintext OTPs or plaintext reset tokens.
    """
    __tablename__ = "password_reset_otps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Primary UUID key for OTP reset session",
    )
    farmer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farmers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Associated farmer ID if registered",
    )
    mobile_number: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        comment="Raw mobile number entered during request",
    )
    normalized_mobile: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        index=True,
        comment="E.164 normalized phone identity (+91XXXXXXXXXX)",
    )
    otp_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Cryptographically hashed OTP (Argon2id)",
    )
    reset_token_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Hash of verified reset token permitted to update password",
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
        comment="Number of incorrect OTP verification attempts",
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=5,
        server_default=text("5"),
        nullable=False,
        comment="Maximum allowed incorrect attempts before session lockout",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="Flag indicating OTP was successfully verified",
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="Flag indicating password reset completed (single use)",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="OTP expiration timestamp in UTC (5 minutes from creation)",
    )
    last_resend_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp of latest OTP dispatch for cooldown enforcement",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Record creation timestamp in UTC",
    )

