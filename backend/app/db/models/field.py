"""
Paddy Farming Assistant - Field ORM Model (STEP 11F.5)
Master registry of monitored agricultural paddy parcels.
"""

import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Numeric, Date, Boolean, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.satellite import SatelliteObservation
    from app.db.models.prediction import PredictionHistory
    from app.db.models.weather import WeatherRecord
    from app.db.models.report import Report


class Field(Base, TimestampMixin):
    """
    Master registry of agricultural fields and parcels.
    Preserves authoritative external IDs (e.g., FIELD_01 to FIELD_58)
    and exact GPS coordinates.
    """
    __tablename__ = "fields"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Surrogate UUID primary key",
    )
    external_field_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Authoritative external natural field identifier (e.g. FIELD_01)",
    )
    clean_field_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Cluster clean field identifier (e.g. CLEAN_FIELD_001)",
    )
    field_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Farmer-friendly custom plot or field name",
    )
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6),
        nullable=False,
        comment="Field centroid WGS84 latitude coordinate (~0.11m precision)",
    )
    longitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6),
        nullable=False,
        comment="Field centroid WGS84 longitude coordinate (~0.11m precision)",
    )
    elevation_m: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Field elevation in meters above sea level",
    )
    area_hectares: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Field surface area in hectares",
    )
    crop_variety: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Planted paddy cultivar or seed variety (e.g. BPT 5204)",
    )
    sowing_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Crop sowing or transplantation date",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
        index=True,
        comment="Active status flag for operational queries",
    )
    is_user_created: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
        index=True,
        comment="Flag indicating if the field was created by a user",
    )

    # Relationships
    satellite_observations: Mapped[List["SatelliteObservation"]] = relationship(
        "SatelliteObservation",
        back_populates="field",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    predictions: Mapped[List["PredictionHistory"]] = relationship(
        "PredictionHistory",
        back_populates="field",
        cascade="save-update, merge",
        passive_deletes=True,
    )
    weather_records: Mapped[List["WeatherRecord"]] = relationship(
        "WeatherRecord",
        back_populates="field",
        cascade="save-update, merge",
        passive_deletes=True,
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="field",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_fields_coordinates", "latitude", "longitude"),
    )

    def __repr__(self) -> str:
        return f"<Field(id={self.id}, external_id='{self.external_field_id}', coords=({self.latitude}, {self.longitude}))>"
