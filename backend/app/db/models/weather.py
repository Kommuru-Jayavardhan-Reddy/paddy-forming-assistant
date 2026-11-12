"""
Paddy Farming Assistant - WeatherRecord ORM Model (STEP 11F.5)
Stores atmospheric observations and multi-day forecast summaries from Open-Meteo.
"""

import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    SmallInteger,
    Numeric,
    Date,
    String,
    DateTime,
    ForeignKey,
    Identity,
    CheckConstraint,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.field import Field


class WeatherRecord(Base):
    """
    Atmospheric weather readings.
    Strictly decouples real-time actual atmospheric observations ('current')
    from forward-looking predictive models ('forecast').
    """
    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        comment="Auto-incrementing 64-bit weather record identifier",
    )
    field_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fields.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated agricultural field (nullable for ad-hoc coordinate queries)",
    )
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6),
        nullable=False,
        comment="Observation location WGS84 latitude",
    )
    longitude: Mapped[Decimal] = mapped_column(
        Numeric(9, 6),
        nullable=False,
        comment="Observation location WGS84 longitude",
    )
    record_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Meteorological record type: 'current' (observed) or 'forecast' (predicted)",
    )
    observation_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Actual recorded atmospheric observation timestamp in UTC (for current records)",
    )
    forecast_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Target calendar forecast date (for forecast records)",
    )
    retrieval_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when query was retrieved from upstream provider in UTC",
    )
    temperature_c: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Surface air temperature at 2m in Celsius",
    )
    temperature_max_c: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Daily maximum forecasted temperature in Celsius",
    )
    temperature_min_c: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Daily minimum forecasted temperature in Celsius",
    )
    relative_humidity_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Relative humidity at 2m (0.00 to 100.00%)",
    )
    precipitation_mm: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Current precipitation or daily precipitation sum in millimeters",
    )
    rain_mm: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Current rain rate or daily rain sum in millimeters",
    )
    wind_speed_kmh: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Surface wind speed at 10m in km/h",
    )
    wind_speed_max_kmh: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Maximum forecasted wind gust speed in km/h",
    )
    weather_code: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="World Meteorological Organization (WMO) numeric weather code",
    )
    weather_condition: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Human-readable weather description (e.g. 'Overcast', 'Moderate rain')",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        default="Open-Meteo",
        server_default=text("'Open-Meteo'"),
        nullable=False,
        comment="Meteorological data provider service name",
    )
    timezone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Provider local timezone identifier (e.g. 'Asia/Kolkata')",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Ingestion timestamp in UTC",
    )

    # Relationships
    field: Mapped[Optional["Field"]] = relationship(
        "Field",
        back_populates="weather_records",
    )

    __table_args__ = (
        CheckConstraint(
            "record_type IN ('current', 'forecast')",
            name="ck_weather_record_type",
        ),
        Index("idx_weather_field_retrieval", "field_id", "retrieval_time"),
        Index("idx_weather_coords_type", "latitude", "longitude", "record_type", "retrieval_time"),
        Index("idx_weather_forecast_date", "field_id", "forecast_date"),
    )

    def __repr__(self) -> str:
        return f"<WeatherRecord(id={self.id}, type='{self.record_type}', temp={self.temperature_c}°C)>"
