"""
Paddy Farming Assistant - Database Module (STEP 11F.3)
Exposes database session management, engine lifecycle, and connectivity checks.
"""

from app.db.session import (
    get_db,
    get_async_engine,
    init_db_engine,
    close_db_engine,
    check_db_connectivity,
    AsyncSessionLocal,
)
from app.db.base import Base, TimestampMixin
from app.db.models import (
    Field,
    PredictionHistory,
    SatelliteObservation,
    WeatherRecord,
    MarketPrice,
    Buyer,
    Report,
)

__all__ = [
    "get_db",
    "get_async_engine",
    "init_db_engine",
    "close_db_engine",
    "check_db_connectivity",
    "AsyncSessionLocal",
    "Base",
    "TimestampMixin",
    "Field",
    "PredictionHistory",
    "SatelliteObservation",
    "WeatherRecord",
    "MarketPrice",
    "Buyer",
    "Report",
]
