"""
Paddy Farming Assistant - SatelliteObservation ORM Model (STEP 11F.5)
Stores Sentinel-2 L2A vegetation spectral trajectories (NDVI, NDRE, GNDVI) across temporal observations.
"""

import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    SmallInteger,
    Numeric,
    Date,
    Boolean,
    String,
    DateTime,
    ForeignKey,
    Identity,
    CheckConstraint,
    UniqueConstraint,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.field import Field


class SatelliteObservation(Base):
    """
    Time-series vegetation spectral index observation for an agricultural field.
    Stores the 10-timestep Sentinel-2 sequence values (NDVI, NDRE, GNDVI).
    """
    __tablename__ = "satellite_observations"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        comment="Auto-incrementing 64-bit observation identifier",
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to fields.id (cascades on field deletion)",
    )
    time_step: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Normalized sequence index (1 to 10) for model input window",
    )
    observation_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Authoritative Sentinel-2 acquisition date (YYYY-MM-DD)",
    )
    ndvi: Mapped[Decimal] = mapped_column(
        Numeric(7, 6),
        nullable=False,
        comment="Normalized Difference Vegetation Index [-1.000000 to +1.000000]",
    )
    ndre: Mapped[Decimal] = mapped_column(
        Numeric(7, 6),
        nullable=False,
        comment="Normalized Difference Red Edge Index [-1.000000 to +1.000000]",
    )
    gndvi: Mapped[Decimal] = mapped_column(
        Numeric(7, 6),
        nullable=False,
        comment="Green Normalized Difference Vegetation Index [-1.000000 to +1.000000]",
    )
    cloud_coverage_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Scene or granule cloud coverage percentage (0.00 to 100.00)",
    )
    is_interpolated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        comment="True if value was regularized via linear temporal interpolation",
    )
    data_source: Mapped[str] = mapped_column(
        String(50),
        default="Sentinel-2 L2A",
        server_default=text("'Sentinel-2 L2A'"),
        nullable=False,
        comment="Spectral satellite sensor / processing level",
    )
    raw_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Satellite metadata: spacecraft ID, tile name, orbit, solar geometry",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Database ingestion timestamp in UTC",
    )

    # Relationships
    field: Mapped["Field"] = relationship(
        "Field",
        back_populates="satellite_observations",
    )

    __table_args__ = (
        # Prevent duplicate entries for the same field, date, and constellation
        UniqueConstraint(
            "field_id",
            "observation_date",
            "data_source",
            name="uq_sat_field_date_source",
        ),
        CheckConstraint(
            "time_step IS NULL OR (time_step >= 1 AND time_step <= 100)",
            name="ck_sat_timestep",
        ),
        CheckConstraint(
            "ndvi >= -1.0 AND ndvi <= 1.0",
            name="ck_sat_ndvi",
        ),
        CheckConstraint(
            "ndre >= -1.0 AND ndre <= 1.0",
            name="ck_sat_ndre",
        ),
        CheckConstraint(
            "gndvi >= -1.0 AND gndvi <= 1.0",
            name="ck_sat_gndvi",
        ),
        Index("idx_sat_field_date", "field_id", "observation_date"),
    )

    def __repr__(self) -> str:
        return f"<SatelliteObservation(field_id={self.field_id}, date={self.observation_date}, ndvi={self.ndvi})>"
