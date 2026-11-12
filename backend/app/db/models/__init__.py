"""
Paddy Farming Assistant - Database ORM Models Subpackage (STEP 11F.5)
Central registry exporting all seven SQLAlchemy 2.x declarative models.
"""

from app.db.base import Base, TimestampMixin
from app.db.models.field import Field
from app.db.models.prediction import PredictionHistory
from app.db.models.satellite import SatelliteObservation
from app.db.models.weather import WeatherRecord
from app.db.models.market import MarketPrice
from app.db.models.buyer import Buyer
from app.db.models.report import Report
from app.db.models.farmer import Farmer
from app.db.models.password_reset import PasswordResetOTP

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
    "Farmer",
    "PasswordResetOTP",
]
