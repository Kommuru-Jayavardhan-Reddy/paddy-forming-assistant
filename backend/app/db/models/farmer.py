"""
Paddy Farming Assistant - Farmer ORM Model (STEP 2C Hardened)
Master registry of authenticated farmers and administrators with database-enforced multi-tenant isolation.
Uses encrypted database secrets (Fernet/AES-GCM) and nullable E.164 mobile numbers without inventing fake identities.
"""

import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, func, text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.prediction import PredictionHistory


class UserRole(str, Enum):
    FARMER = "farmer"
    ADMIN = "admin"


class Farmer(Base):
    """
    Farmer entity model representing a registered agricultural user or system administrator.
    Maintains user identity, Argon2id credentials, normalized E.164 phone identity,
    and references the isolated tenant PostgreSQL schema.
    """
    __tablename__ = "farmers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Surrogate UUID primary key for farmer entity",
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique login handle or username",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Cryptographically salted Argon2id password hash",
    )
    mobile_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Raw phone number supplied during registration (nullable for legacy/unverified accounts)",
    )
    normalized_mobile: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
        index=True,
        comment="Strict E.164 normalized mobile identity e.g. +919876543210 (unique across non-null values)",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.FARMER.value,
        server_default=text("'farmer'"),
        nullable=False,
        comment="User role: 'farmer' or 'admin'",
    )
    schema_name: Mapped[Optional[str]] = mapped_column(
        String(63),
        unique=True,
        nullable=True,
        index=True,
        comment="Dedicated PostgreSQL schema name (NULL for admin)",
    )
    encrypted_db_secret: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Authenticated ciphertext of tenant database identity secret (NULL for admin; never plaintext)",
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Farmer personal full name",
    )
    farm_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Name of the agricultural holding or farm",
    )
    village: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Village or locality location",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        comment="Active account status flag",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Account creation timestamp in UTC",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Record last update timestamp in UTC",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('farmer', 'admin')",
            name="chk_farmers_role_valid"
        ),
        CheckConstraint(
            "normalized_mobile IS NULL OR normalized_mobile ~ '^\\+[1-9][0-9]{7,14}$'",
            name="chk_farmers_e164_mobile"
        ),
        CheckConstraint(
            "(role = 'admin' AND schema_name IS NULL) OR (role = 'farmer' AND (schema_name IS NULL OR schema_name ~ '^farmer_[a-f0-9]{16}$'))",
            name="chk_farmers_schema_format"
        ),
    )

    # Relationships
    predictions: Mapped[List["PredictionHistory"]] = relationship(
        "PredictionHistory",
        back_populates="farmer",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        # Strictly exclude password_hash and encrypted_db_secret from string representations
        return f"<Farmer(id={self.id}, username='{self.username}', role='{self.role}', schema='{self.schema_name}')>"
