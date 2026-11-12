"""
Paddy Farming Assistant - MarketPrice ORM Model (STEP 11F.5)
Stores official mandi agricultural market spot prices for paddy/rice commodities.
"""

from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Numeric,
    Date,
    String,
    DateTime,
    Identity,
    CheckConstraint,
    UniqueConstraint,
    Index,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketPrice(Base):
    """
    Physical agricultural wholesale mandi commodity prices.
    Grounded in open official records (e.g. Agmarknet / e-NAM).
    """
    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
        comment="Auto-incrementing 64-bit market price record ID",
    )
    market_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
        comment="Physical regulated market or mandi yard name (e.g. 'Tirupati Mandi')",
    )
    district: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Administrative district name (e.g. 'Chittoor')",
    )
    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Administrative state name (e.g. 'Andhra Pradesh')",
    )
    commodity: Mapped[str] = mapped_column(
        String(100),
        default="Paddy (Dhan)",
        server_default=text("'Paddy (Dhan)'"),
        nullable=False,
        comment="Commodity name (standardized as Paddy/Dhan)",
    )
    variety: Mapped[str] = mapped_column(
        String(100),
        default="Common",
        server_default=text("'Common'"),
        nullable=False,
        comment="Crop trade variety or cultivar (e.g. 'BPT 5204', 'Grade-A', 'Common')",
    )
    grade: Mapped[str] = mapped_column(
        String(50),
        default="FAQ",
        server_default=text("'FAQ'"),
        nullable=False,
        comment="Standardized trade grade (e.g. 'FAQ', 'Medium', 'Fine')",
    )
    min_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Minimum transaction price recorded per unit",
    )
    max_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Maximum transaction price recorded per unit",
    )
    modal_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Modal (benchmark/representative) transaction price per unit",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        server_default=text("'INR'"),
        nullable=False,
        comment="Currency ISO symbol (e.g. 'INR')",
    )
    unit: Mapped[str] = mapped_column(
        String(30),
        default="Quintal",
        server_default=text("'Quintal'"),
        nullable=False,
        comment="Trade measure unit (default 1 Quintal = 100 kg)",
    )
    price_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date quotation was posted in the market (YYYY-MM-DD)",
    )
    source: Mapped[str] = mapped_column(
        String(100),
        default="Agmarknet",
        server_default=text("'Agmarknet'"),
        nullable=False,
        comment="Official public portal or source of the mandi quote",
    )
    retrieval_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Data ingestion timestamp in UTC",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Record creation timestamp in UTC",
    )

    __table_args__ = (
        UniqueConstraint(
            "market_name",
            "commodity",
            "variety",
            "price_date",
            name="uq_market_quote",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "min_price >= 0 AND max_price >= min_price AND modal_price >= min_price AND modal_price <= max_price",
            name="ck_market_prices",
        ),
        Index("idx_market_lookup", "state", "district", "commodity", "price_date"),
    )

    def __repr__(self) -> str:
        return f"<MarketPrice(market='{self.market_name}', commodity='{self.commodity}', modal={self.modal_price} {self.currency}/{self.unit})>"
