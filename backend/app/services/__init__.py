"""
Service Layer for Business and Prediction Logic
"""

from app.services.prediction import PredictionService
from app.services.field_mapping import FieldMappingService
from app.services.multimodal_prediction import MultimodalPredictionService
from app.services.field_health import FieldHealthService
from app.services.gradcam import GradCAMService, gradcam_service
from app.services.shap_service import SHAPService, shap_service
from app.services.weather_service import (
    WeatherService,
    weather_service,
    get_weather_for_field,
    get_current_weather_for_field,
    get_forecast_for_field,
)

__all__ = [
    "PredictionService",
    "FieldMappingService",
    "MultimodalPredictionService",
    "FieldHealthService",
    "GradCAMService",
    "gradcam_service",
    "SHAPService",
    "shap_service",
    "WeatherService",
    "weather_service",
    "get_weather_for_field",
    "get_current_weather_for_field",
    "get_forecast_for_field",
]



