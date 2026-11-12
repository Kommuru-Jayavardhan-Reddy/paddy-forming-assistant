"""
Paddy Farming Assistant - Buyer ORM Model (STEP 11F.5)
Directory of verified wholesale agricultural buyers, millers, and procurement agencies.
"""

import uuid
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    String,
    Text,
    Numeric,
    Boolean,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Buyer(Base, TimestampMixin):
    """
    Verified grain buyer, miller, or agricultural procurement enterprise.
    Designed with privacy protections by keeping personal data minimal.
    """
    __tablename__ = "buyers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Unique buyer identifier",
    )
    business_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        comment="Registered legal enterprise or business trade name",
    )
    buyer_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Entity category: 'mill', 'fpo', 'government_agency', 'wholesaler', 'trader'",
    )
    district: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Administrative district location",
    )
    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Administrative state location",
    )
    address_summary: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="General business yard or market location address",
    )
    contact_person: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Designated representative / procurement officer name",
    )
    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Verified business contact phone number",
    )
    contact_email: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Verified business contact email address",
    )
    preferred_varieties: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="JSONB array of accepted paddy varieties (e.g. ['BPT 5204', 'IR 64'])",
    )
    min_procurement_quintals: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="Minimum batch procurement quantity in quintals",
    )
    verification_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default=text("'pending'"),
        nullable=False,
        comment="Verification state: 'verified', 'pending', or 'unverified'",
    )
    verification_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal administrative verification audit notes",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        index=True,
        comment="Operational active status flag",
    )
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(9, 6),
        nullable=True,
        comment="WGS84 latitude coordinate (~0.11m precision)",
    )
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(9, 6),
        nullable=True,
        comment="WGS84 longitude coordinate (~0.11m precision)",
    )
    coordinate_source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Provenance or source authority of verified coordinates",
    )

    __table_args__ = (
        CheckConstraint(
            "buyer_type IN ('mill', 'fpo', 'government_agency', 'wholesaler', 'trader')",
            name="ck_buyer_type",
        ),
        CheckConstraint(
            "verification_status IN ('verified', 'pending', 'unverified')",
            name="ck_buyer_verification_status",
        ),
        Index("idx_buyers_location", "state", "district", "is_active"),
        Index("idx_buyers_status", "verification_status", "is_active"),
        Index("idx_buyers_coordinates", "latitude", "longitude"),
        Index("idx_buyers_varieties_gin", "preferred_varieties", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Buyer(id={self.id}, name='{self.business_name}', type='{self.buyer_type}', status='{self.verification_status}')>"
