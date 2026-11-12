"""
Paddy Farming Assistant - SQLAlchemy Declarative Base (STEP 11F.5)
Defines the shared DeclarativeBase with Alembic-compatible constraint naming conventions
and reusable timestamp mixins for all PostgreSQL ORM models.
"""

from datetime import datetime, timezone
from sqlalchemy import MetaData, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit naming conventions for constraints and indexes to support deterministic Alembic migrations
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Shared Declarative Base class for all Paddy Farming Assistant ORM models.
    Enforces standardized naming conventions across PostgreSQL tables.
    """
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """
    Reusable mixin providing timezone-aware created_at and updated_at UTC timestamps.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Record creation timestamp in UTC",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Last modification timestamp in UTC",
    )
