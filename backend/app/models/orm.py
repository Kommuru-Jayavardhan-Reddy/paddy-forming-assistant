"""
Paddy Farming Assistant - Database ORM Models Adapter
Re-exports the 7 SQLAlchemy ORM models from app.db.models for convenience,
preventing namespace collisions with AI PyTorch model architectures in app.models.
"""

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
