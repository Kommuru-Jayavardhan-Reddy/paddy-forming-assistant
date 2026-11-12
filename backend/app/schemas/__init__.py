"""
Paddy Farming Assistant - Schemas Package
"""

from app.schemas.timeseries import SatelliteTimestep, SatelliteTimeSeriesResponse
from app.schemas.multimodal import MultimodalPredictionResponse, MultimodalTopPrediction
from app.schemas.field_health import (
    FieldHealthResponse,
    VegetationIndexValues,
    IndexTrendMetric,
    IndexSummaryStatistics,
    FieldDataQualityStatus,
)
from app.schemas.gradcam import GradCAMResponse
from app.schemas.shap import (
    TimestepFeatureAttribution,
    FeatureImportanceSummary,
    StrongestContribution,
    SHAPExplanationResponse,
)
from app.schemas.weather import (
    WeatherCoordinates,
    WeatherUnits,
    CurrentWeatherObservation,
    DailyForecastItem,
    CurrentWeatherResponse,
    WeatherForecastResponse,
    FieldWeatherResponse,
)
from app.schemas.field import (
    FieldItemResponse,
    FieldListResponse,
    FieldDetailResponse,
)
from app.schemas.market import (
    MarketPriceItem,
    MarketPriceListResponse,
    MarketSyncResponse,
    MarketSummaryResponse,
    DailyTrendPoint,
    MarketTrendsResponse,
    DistrictPriceBenchmark,
    DistrictAnalyticsResponse,
    VarietyPriceBenchmark,
    VarietyAnalyticsResponse,
)
from app.schemas.buyer import (
    BuyerItem,
    BuyerListResponse,
)
from app.schemas.report import (
    ReportResponse,
    ReportListResponse,
    ReportGenerateRequest,
)

__all__ = [
    "SatelliteTimestep",
    "SatelliteTimeSeriesResponse",
    "MultimodalPredictionResponse",
    "MultimodalTopPrediction",
    "FieldHealthResponse",
    "VegetationIndexValues",
    "IndexTrendMetric",
    "IndexSummaryStatistics",
    "FieldDataQualityStatus",
    "GradCAMResponse",
    "TimestepFeatureAttribution",
    "FeatureImportanceSummary",
    "StrongestContribution",
    "SHAPExplanationResponse",
    "WeatherCoordinates",
    "WeatherUnits",
    "CurrentWeatherObservation",
    "DailyForecastItem",
    "CurrentWeatherResponse",
    "WeatherForecastResponse",
    "FieldWeatherResponse",
    "FieldItemResponse",
    "FieldListResponse",
    "FieldDetailResponse",
    "MarketPriceItem",
    "MarketPriceListResponse",
    "MarketSyncResponse",
    "MarketSummaryResponse",
    "DailyTrendPoint",
    "MarketTrendsResponse",
    "DistrictPriceBenchmark",
    "DistrictAnalyticsResponse",
    "VarietyPriceBenchmark",
    "VarietyAnalyticsResponse",
    "BuyerItem",
    "BuyerListResponse",
    "ReportResponse",
    "ReportListResponse",
    "ReportGenerateRequest",
]

