from datetime import datetime, date, timezone
import hashlib
import uuid
import io
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from PIL import Image

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status, Response, Query, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.exceptions import (
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFormatError,
    CorruptedImageError,
    ModelUnavailableError,
    ModelInferenceError,
    FieldNotFoundError,
    SatelliteDataUnavailableError,
    InvalidCoordinatesError,
    InvalidForecastDaysError,
    WeatherServiceDisabledError,
    WeatherServiceUnavailableError,
    WeatherProviderError,
    WeatherParsingError,
    BuyerNotFoundError,
    MarketServiceDisabledError,
    MarketApiKeyMissingError,
    MarketProviderError,
    MarketServiceUnavailableError,
    MarketParsingError,
)
from app.db.session import get_db
from app.db.repositories.field_repository import FieldRepository
from app.db.repositories.satellite_repository import SatelliteRepository
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.weather_repository import WeatherRepository
from app.db.repositories.other_repositories import MarketPriceRepository, BuyerRepository, ReportRepository
from app.models.model_loader import ModelLoader
from app.models.multimodal_model import MultimodalModelLoader
from app.schemas.field import FieldDetailResponse, FieldCreateRequest, FieldGpsExtractResponse
from app.schemas.prediction import PredictionRecordResponse, PredictionListResponse
from app.schemas.report import ReportResponse, ReportListResponse, ReportGenerateRequest
from app.schemas.market import (
    MarketPriceItem,
    MarketPriceListResponse,
    MarketSyncResponse,
    MarketSummaryResponse,
    MarketTrendsResponse,
    DistrictAnalyticsResponse,
    VarietyAnalyticsResponse,
)
from app.schemas.buyer import (
    BuyerItem,
    BuyerListResponse,
    BuyerNearbyItem,
    BuyerNearbyResponse,
)
from app.schemas.timeseries import SatelliteTimeSeriesResponse
from app.schemas.multimodal import MultimodalPredictionResponse
from app.schemas.field_health import FieldHealthResponse, FieldHealthSummaryResponse
from app.schemas.gradcam import GradCAMResponse
from app.schemas.shap import SHAPExplanationResponse
from app.schemas.weather import (
    CurrentWeatherResponse,
    CurrentWeatherObservation,
    WeatherForecastResponse,
    FieldWeatherResponse,
)
from app.services.prediction import PredictionService
from app.services.field_mapping import FieldMappingService
from app.services.multimodal_prediction import MultimodalPredictionService
from app.services.field_health import FieldHealthService
from app.services.gradcam import GradCAMService, gradcam_service
from app.services.shap_service import SHAPService, shap_service
from app.services.weather_service import weather_service
from app.services.market_service import MarketService
from app.services.report_service import ReportService
from app.services.ocr_gps_service import ocr_gps_service


logger = logging.getLogger(__name__)
router = APIRouter()



@router.get("/health", summary="Service Health Check", tags=["System"])
async def health_check(response: Response):
    """
    Returns application operational health status.
    Fast and lightweight; does not perform heavyweight model loading.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return {
        "status": "healthy",
        "service": config.PROJECT_NAME,
        "version": config.API_VERSION,
    }


@router.get("/health/model", summary="Model In-Memory Status", tags=["System"])
async def model_health_check(response: Response):
    """
    Returns lightweight in-memory loading status of the AI models.
    Does not trigger heavyweight model loading or inference.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    model_status = ModelLoader.get_model_status()
    checkpoint_available = config.EFFICIENTNET_CHECKPOINT_PATH.exists()
    multimodal_status = MultimodalModelLoader.get_status()
    multimodal_checkpoint_available = config.MULTIMODAL_CHECKPOINT_PATH.exists()

    return {
        "status": model_status,
        "model_loaded": ModelLoader.is_model_loaded(),
        "device": config.DEVICE,
        "checkpoint_available": checkpoint_available,
        "multimodal_status": multimodal_status,
        "multimodal_model_loaded": MultimodalModelLoader.is_loaded(),
        "multimodal_checkpoint_available": multimodal_checkpoint_available,
    }


@router.get("/health/database", summary="Database Connectivity Status", tags=["System"])
async def database_health_check(response: Response):
    """
    Checks PostgreSQL connectivity and returns operational status using SQLAlchemy.
    Never exposes credentials, connection strings, or internal stack traces.
    Returns HTTP 200 with status='healthy' if connected, or HTTP 503 with status='unhealthy'.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    from app.db.session import check_db_connectivity
    db_status = await check_db_connectivity()

    if not db_status.get("connected"):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return db_status


@router.get("/classes", summary="Get Supported Paddy Disease Classes", tags=["Metadata"])
async def get_disease_classes():
    """
    Returns the list of supported 13 paddy disease classes.
    Matches frontend getClasses() expectation.
    """
    return {
        "classes": config.DISEASE_CLASSES,
        "total_classes": config.NUM_CLASSES,
    }


@router.get("/fields", summary="List All Catalog Fields", tags=["Fields"])
async def list_catalog_fields(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum items to return"),
    user_only: Optional[bool] = Query(None, description="Filter only user-entered fields (True) or all (None)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns verified agricultural fields with metadata and geographic coordinates.
    Directly retrieves records from the PostgreSQL 'fields' table with pagination support.
    When user_only=True, only fields entered and saved by the user are returned.
    """
    field_repo = FieldRepository(db)
    db_fields, total_count = await field_repo.list_fields(
        skip=skip, limit=limit, active_only=True, user_only=user_only
    )

    # Active dataset image pairing lookup
    service = FieldMappingService.get_instance()
    active_fields = set()
    if service.is_loaded:
        active_fields = set(r["nearest_satellite_field"] for r in service._dataset_images.values())

    fields_list = []
    for f in db_fields:
        fid = f.external_field_id
        seq_idx = int(fid.split("_")[1]) - 1 if "_" in fid and fid.split("_")[1].isdigit() else 0
        fields_list.append({
            "field_id": fid,
            "external_field_id": fid,
            "clean_field_id": f.clean_field_id,
            "field_name": f.field_name,
            "latitude": float(f.latitude),
            "longitude": float(f.longitude),
            "area_hectares": float(f.area_hectares) if f.area_hectares is not None else None,
            "crop_variety": f.crop_variety,
            "is_active": f.is_active,
            "is_user_created": bool(f.is_user_created),
            "sentinel2_image_count": 10,
            "embedding_index": seq_idx,
            "sequence_index": seq_idx,
            "has_images": fid in active_fields,
        })

    return {
        "fields": fields_list,
        "total_fields": total_count,
    }


@router.post(
    "/fields",
    response_model=FieldDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and Store New User Field in Database",
    tags=["Fields"],
)
async def create_user_field(
    payload: FieldCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new agricultural field entered by the user and persists it in PostgreSQL.
    Guarantees unique external_field_id (auto-generating if omitted).
    Registers the field with FieldMappingService for satellite observation linkage.
    """
    field_repo = FieldRepository(db)
    service = FieldMappingService.get_instance()

    # Generate or normalize external_field_id
    if payload.external_field_id and payload.external_field_id.strip():
        ext_id = payload.external_field_id.strip()
        existing = await field_repo.get_by_external_id(ext_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Field with ID '{ext_id}' already exists in database.",
            )
    else:
        # Auto-generate unique ID e.g. FIELD_USER_01, FIELD_USER_02...
        _, count = await field_repo.list_fields(active_only=False, user_only=True)
        num = count + 1
        ext_id = f"FIELD_USER_{num:02d}"
        while await field_repo.get_by_external_id(ext_id):
            num += 1
            ext_id = f"FIELD_USER_{num:02d}"

    field = await field_repo.create_field(
        external_field_id=ext_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        field_name=payload.field_name.strip(),
        area_hectares=payload.area_hectares,
        crop_variety=payload.crop_variety.strip() if payload.crop_variety else None,
        is_active=True,
        is_user_created=True,
    )
    await db.commit()
    await db.refresh(field)

    # Register in memory for satellite sequence analysis
    service.register_custom_field(
        field_id=ext_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        field_name=payload.field_name.strip(),
    )

    return {
        "id": field.id,
        "field_id": field.external_field_id,
        "external_field_id": field.external_field_id,
        "clean_field_id": field.clean_field_id,
        "field_name": field.field_name,
        "latitude": float(field.latitude),
        "longitude": float(field.longitude),
        "area_hectares": float(field.area_hectares) if field.area_hectares is not None else None,
        "crop_variety": field.crop_variety,
        "is_active": field.is_active,
        "has_images": False,
        "is_user_created": True,
        "observation_count": 0,
    }


@router.post(
    "/fields/extract-gps",
    response_model=FieldGpsExtractResponse,
    summary="Extract GPS Coordinates from Uploaded Photo (EXIF or OCR)",
    tags=["Fields"],
)
async def extract_gps_endpoint(
    file: UploadFile = File(..., description="Uploaded field leaf photo"),
):
    """
    Two-stage GPS extraction from uploaded image:
    1. EXIF GPS Metadata (Primary)
    2. Computer Vision + Tesseract OCR (Fallback for GPS Map Camera overlays)
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    result = await run_in_threadpool(ocr_gps_service.extract_gps, contents)
    return result



@router.get(
    "/fields/{field_id}",
    response_model=FieldDetailResponse,
    summary="Get Detailed Field Record",
    tags=["Fields"],
)
async def get_field_by_id_endpoint(
    field_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full details for a single field from PostgreSQL by its external ID (e.g. 'FIELD_01').
    Returns HTTP 404 if the field does not exist.
    """
    field_repo = FieldRepository(db)
    field = await field_repo.get_by_external_id(field_id)
    if not field:
        raise FieldNotFoundError(f"Field '{field_id}' was not found in the master field catalog.")

    sat_repo = SatelliteRepository(db)
    obs = await sat_repo.get_observations_by_field_uuid(field.id)

    service = FieldMappingService.get_instance()
    active_fields = set()
    if service.is_loaded:
        active_fields = set(r["nearest_satellite_field"] for r in service._dataset_images.values())

    seq_idx = int(field.external_field_id.split("_")[1]) - 1 if "_" in field.external_field_id and field.external_field_id.split("_")[1].isdigit() else 0

    return FieldDetailResponse(
        id=field.id,
        field_id=field.external_field_id,
        external_field_id=field.external_field_id,
        clean_field_id=field.clean_field_id,
        field_name=field.field_name,
        latitude=float(field.latitude),
        longitude=float(field.longitude),
        area_hectares=float(field.area_hectares) if field.area_hectares is not None else None,
        crop_variety=field.crop_variety,
        elevation_m=float(field.elevation_m) if field.elevation_m is not None else None,
        sowing_date=field.sowing_date,
        is_active=field.is_active,
        has_images=field.external_field_id in active_fields,
        observation_count=len(obs),
    )


@router.get(
    "/fields/{field_id}/timeseries",
    response_model=SatelliteTimeSeriesResponse,
    summary="Get Satellite Time-Series for Field",
    tags=["Satellite Time-Series"],
)
async def get_field_timeseries(
    field_id: str,
    start_date: Optional[date] = Query(None, description="Optional start observation date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Optional end observation date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the chronological Sentinel-2 satellite time-series observations from PostgreSQL.
    Features: NDVI, NDRE, GNDVI.
    Resolves the external field identifier against the 'fields' table and queries 'satellite_observations'.
    Returns HTTP 404 if field_id is unknown.
    Returns HTTP 503 if satellite sequence data is unavailable or missing.
    """
    sat_repo = SatelliteRepository(db)
    field, observations = await sat_repo.get_observations_by_external_id(
        field_id=field_id,
        start_date=start_date,
        end_date=end_date,
    )

    if field is None:
        raise FieldNotFoundError(f"Field '{field_id}' was not found in the master field catalog.")

    if not observations:
        raise SatelliteDataUnavailableError(f"No satellite observations available for field '{field.external_field_id}'.")

    seq_idx = int(field.external_field_id.split("_")[1]) - 1 if "_" in field.external_field_id and field.external_field_id.split("_")[1].isdigit() else 0

    timesteps = []
    for i, obs in enumerate(observations):
        timesteps.append({
            "timestep": obs.time_step if obs.time_step is not None else (i + 1),
            "date": obs.observation_date.strftime("%Y-%m-%d") if obs.observation_date else None,
            "ndvi": float(obs.ndvi),
            "ndre": float(obs.ndre),
            "gndvi": float(obs.gndvi),
        })

    return {
        "field_id": field.external_field_id,
        "clean_field_id": field.clean_field_id,
        "sequence_index": seq_idx,
        "features": config.SATELLITE_FEATURES,
        "total_timesteps": len(timesteps),
        "coordinates": {
            "latitude": round(float(field.latitude), 6),
            "longitude": round(float(field.longitude), 6),
        },
        "has_dates": all(t["date"] is not None for t in timesteps),
        "timesteps": timesteps,
    }


@router.get(
    "/fields/health-summary",
    response_model=FieldHealthSummaryResponse,
    summary="Get Aggregated Fields Health Summary",
    tags=["Field Health"],
)
async def get_fields_health_summary():
    """
    Computes aggregate vegetation health classification across all registered
    Sentinel-2 monitored fields using calibrated agronomic NDVI thresholds:
    - Healthy (High Vigor): NDVI >= 0.60
    - Needs Attention (Moderate): 0.35 <= NDVI < 0.60
    - High Risk (Vegetation Deficit): NDVI < 0.35
    """
    service = FieldHealthService()
    return service.get_health_summary()


@router.get(
    "/fields/threshold-config",
    summary="Get Field Vegetation Threshold Configuration",
    tags=["Field Health"],
)
async def get_field_threshold_config():
    """
    Returns configurable provisional thresholds, paddy growth-stage registry,
    boundary definitions, and scientific methodology metadata.
    """
    service = FieldHealthService()
    return service.get_threshold_config()


@router.get(
    "/fields/{field_id}/health",
    response_model=FieldHealthResponse,
    summary="Get Field Vegetation Health and Trends",
    tags=["Field Health"],
)
async def get_field_health(
    field_id: str,
    growth_stage: Optional[str] = Query(None, description="Optional paddy growth stage (e.g. Tillering, Heading)"),
):
    """
    Computes field-level vegetation health metrics and temporal trends
    from verified Sentinel-2 satellite time-series data.
    Features: NDVI, NDRE, GNDVI.
    Resolves the field against the authoritative master catalog.
    Returns HTTP 404 if field_id is unknown.
    Returns HTTP 503 if satellite sequence data is unavailable or malformed.
    """
    service = FieldHealthService()
    health_data = service.get_field_health(field_id, growth_stage=growth_stage)
    return health_data


# =====================================================================
# Weather Endpoints (STEP 11E.4)
# =====================================================================

@router.get(
    "/weather/current",
    response_model=CurrentWeatherResponse,
    summary="Get Current Weather Conditions",
    tags=["Weather"],
)
async def get_current_weather_endpoint(
    latitude: float = Query(..., description="WGS84 latitude coordinate (-90.0 to 90.0)"),
    longitude: float = Query(..., description="WGS84 longitude coordinate (-180.0 to 180.0)"),
    timezone: str = Query("Asia/Kolkata", description="IANA timezone identifier (e.g., Asia/Kolkata)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves real-time atmospheric observations from Open-Meteo for specified coordinates.
    Metrics: Temperature, Relative Humidity, Precipitation, Rainfall, Wind Speed, Weather Condition.
    Caches genuine observations in PostgreSQL 'weather_records' table.
    Returns HTTP 400 if coordinates are out of valid geographic ranges.
    Returns HTTP 503 if the weather service is disabled or provider is unreachable.
    Returns HTTP 502 if upstream provider returns an error or malformed payload.
    """
    if not config.WEATHER_SERVICE_ENABLED:
        raise WeatherServiceDisabledError("Weather service is disabled by configuration.")
    weather_service.validate_coordinates(latitude, longitude)
    weather_repo = WeatherRepository(db)

    # 1. Check recent cached observation (max age 30 minutes)
    try:
        cached = await weather_repo.get_cached_current_weather(
            latitude=latitude,
            longitude=longitude,
            max_age_minutes=30,
        )
        if cached:
            from app.schemas.weather import WeatherCoordinates, WeatherUnits
            return CurrentWeatherResponse(
                provider="Open-Meteo",
                coordinates=WeatherCoordinates(
                    latitude=float(cached.latitude),
                    longitude=float(cached.longitude),
                    elevation=0.0,
                ),
                timezone=cached.timezone or timezone,
                current=CurrentWeatherObservation(
                    time=cached.observation_time.isoformat() if cached.observation_time else (cached.retrieval_time.isoformat() if cached.retrieval_time else None),
                    temperature=float(cached.temperature_c) if cached.temperature_c is not None else None,
                    relative_humidity=float(cached.relative_humidity_pct) if cached.relative_humidity_pct is not None else None,
                    precipitation=float(cached.precipitation_mm) if cached.precipitation_mm is not None else None,
                    rain=float(cached.rain_mm) if cached.rain_mm is not None else None,
                    wind_speed=float(cached.wind_speed_kmh) if cached.wind_speed_kmh is not None else None,
                    weather_code=cached.weather_code,
                    weather_condition=cached.weather_condition,
                ),
                units=WeatherUnits(),
            )
    except Exception as cache_err:
        logger.debug("Weather cache read bypass: %s", cache_err)

    # 2. Fetch fresh atmospheric observation
    weather_data = await run_in_threadpool(
        weather_service.get_current_weather,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
    )

    # 3. Cache genuine response to PostgreSQL
    try:
        curr = weather_data.get("current") if isinstance(weather_data, dict) else getattr(weather_data, "current", None)
        if curr:
            temp = curr.get("temperature") if isinstance(curr, dict) else getattr(curr, "temperature", None)
            rh = curr.get("relative_humidity") if isinstance(curr, dict) else getattr(curr, "relative_humidity", None)
            precip = curr.get("precipitation") if isinstance(curr, dict) else getattr(curr, "precipitation", None)
            rain_val = curr.get("rain") if isinstance(curr, dict) else getattr(curr, "rain", None)
            wind = curr.get("wind_speed") if isinstance(curr, dict) else getattr(curr, "wind_speed", None)
            w_code = curr.get("weather_code") if isinstance(curr, dict) else getattr(curr, "weather_code", None)
            w_cond = curr.get("weather_condition") if isinstance(curr, dict) else getattr(curr, "weather_condition", None)

            await weather_repo.record_current_weather(
                latitude=latitude,
                longitude=longitude,
                temperature_c=temp,
                relative_humidity_pct=rh,
                precipitation_mm=precip,
                rain_mm=rain_val,
                wind_speed_kmh=wind,
                weather_code=w_code,
                weather_condition=w_cond,
                provider="Open-Meteo",
                timezone_str=timezone,
            )
            await db.commit()
    except Exception as db_err:
        await db.rollback()
        logger.warning("Could not persist current weather observation to database: %s", db_err)

    return weather_data


@router.get(
    "/weather/forecast",
    response_model=WeatherForecastResponse,
    summary="Get Multi-Day Weather Forecast",
    tags=["Weather"],
)
async def get_weather_forecast_endpoint(
    latitude: float = Query(..., description="WGS84 latitude coordinate (-90.0 to 90.0)"),
    longitude: float = Query(..., description="WGS84 longitude coordinate (-180.0 to 180.0)"),
    forecast_days: int = Query(7, description="Number of daily forecast steps (1 to 7)"),
    timezone: str = Query("Asia/Kolkata", description="IANA timezone identifier (e.g., Asia/Kolkata)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves multi-day daily weather forecasts from Open-Meteo for specified coordinates.
    Metrics per day: Max/Min Temperature, Precipitation Sum, Rain Sum, Max Wind Speed, Weather Condition.
    Caches genuine forecast summaries into PostgreSQL 'weather_records'.
    Returns HTTP 400 if coordinates are out of bounds or forecast_days is not between 1 and 7.
    Returns HTTP 503 if the weather service is disabled or provider is unreachable.
    Returns HTTP 502 if upstream provider returns an error or malformed payload.
    """
    if not config.WEATHER_SERVICE_ENABLED:
        raise WeatherServiceDisabledError("Weather service is disabled by configuration.")
    weather_service.validate_coordinates(latitude, longitude)
    if forecast_days < 1 or forecast_days > 7:
        raise InvalidForecastDaysError(
            f"Invalid forecast_days '{forecast_days}': must be an integer between 1 and 7."
        )

    forecast_data = await run_in_threadpool(
        weather_service.get_forecast,
        latitude=latitude,
        longitude=longitude,
        forecast_days=forecast_days,
        timezone=timezone,
    )

    # Cache genuine forecast to PostgreSQL
    try:
        weather_repo = WeatherRepository(db)
        daily_items = (
            forecast_data.get("daily_forecast") or forecast_data.get("daily")
            if isinstance(forecast_data, dict)
            else getattr(forecast_data, "daily_forecast", getattr(forecast_data, "daily", []))
        ) or []
        items = []
        for d in daily_items:
            items.append(d if isinstance(d, dict) else d.model_dump())
        await weather_repo.record_forecast_days(
            latitude=latitude,
            longitude=longitude,
            forecast_items=items,
            provider="Open-Meteo",
            timezone_str=timezone,
        )
        await db.commit()
    except Exception as db_err:
        await db.rollback()
        logger.warning("Could not persist weather forecast days to database: %s", db_err)

    return forecast_data


@router.get(
    "/fields/{field_id}/weather",
    response_model=FieldWeatherResponse,
    summary="Get Current Weather and Forecast for Field",
    tags=["Weather"],
)
async def get_field_weather_endpoint(
    field_id: str,
    forecast_days: int = Query(7, description="Number of daily forecast steps (1 to 7)"),
    timezone: Optional[str] = Query(None, description="Optional IANA timezone name (defaults to Asia/Kolkata)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolves authoritative centroid coordinates for a field from PostgreSQL / master field catalog,
    then retrieves both real-time atmospheric measurements and multi-day agro-forecasts in a
    single efficient Open-Meteo API query, caching records with field_id link.
    Returns HTTP 404 if field_id is unknown.
    Returns HTTP 400 if field coordinates or forecast_days are invalid.
    Returns HTTP 503 if the weather service is disabled or provider is unreachable.
    Returns HTTP 502 if upstream provider returns an error or malformed payload.
    """
    if not config.WEATHER_SERVICE_ENABLED:
        raise WeatherServiceDisabledError("Weather service is disabled by configuration.")
    if forecast_days < 1 or forecast_days > 7:
        raise InvalidForecastDaysError(
            f"Invalid forecast_days '{forecast_days}': must be an integer between 1 and 7."
        )

    field_repo = FieldRepository(db)
    field = await field_repo.get_by_external_id(field_id)

    # Use canonical field_id if found, else original string for service resolution
    canonical_id = field.external_field_id if field else field_id

    try:
        field_weather_data = await run_in_threadpool(
            weather_service.get_weather_for_field,
            field_id=canonical_id,
            forecast_days=forecast_days,
            timezone=timezone,
        )
    except (WeatherServiceUnavailableError, WeatherProviderError) as upstream_err:
        if field:
            try:
                weather_repo = WeatherRepository(db)
                cached = await weather_repo.get_cached_current_weather(
                    latitude=float(field.latitude),
                    longitude=float(field.longitude),
                    max_age_minutes=180,
                )
                if cached:
                    cached_forecasts = await weather_repo.get_cached_forecast(
                        latitude=float(field.latitude),
                        longitude=float(field.longitude),
                        forecast_days=forecast_days,
                        max_age_hours=12,
                    )
                    from app.schemas.weather import WeatherCoordinates, WeatherUnits, CurrentWeatherObservation, DailyForecastItem
                    daily_items = []
                    for f in cached_forecasts:
                        daily_items.append(
                            DailyForecastItem(
                                date=f.forecast_date.strftime("%Y-%m-%d") if f.forecast_date else "",
                                temperature_max=float(f.temperature_max_c) if f.temperature_max_c is not None else None,
                                temperature_min=float(f.temperature_min_c) if f.temperature_min_c is not None else None,
                                precipitation_sum=float(f.precipitation_mm) if f.precipitation_mm is not None else None,
                                rain_sum=float(f.rain_mm) if f.rain_mm is not None else None,
                                wind_speed_max=float(f.wind_speed_max_kmh) if f.wind_speed_max_kmh is not None else None,
                                weather_code=f.weather_code,
                                weather_condition=f.weather_condition,
                            )
                        )
                    clean_id_val = getattr(field, "clean_field_id", None)
                    return FieldWeatherResponse(
                        field_id=canonical_id,
                        requested_field_id=field_id,
                        clean_field_id=clean_id_val,
                        provider="Open-Meteo (Cached)",
                        coordinates=WeatherCoordinates(
                            latitude=float(field.latitude),
                            longitude=float(field.longitude),
                            elevation=0.0,
                        ),
                        timezone=cached.timezone or timezone or "Asia/Kolkata",
                        current=CurrentWeatherObservation(
                            time=cached.observation_time.isoformat() if cached.observation_time else (cached.retrieval_time.isoformat() if cached.retrieval_time else None),
                            temperature=float(cached.temperature_c) if cached.temperature_c is not None else None,
                            relative_humidity=float(cached.relative_humidity_pct) if cached.relative_humidity_pct is not None else None,
                            precipitation=float(cached.precipitation_mm) if cached.precipitation_mm is not None else None,
                            rain=float(cached.rain_mm) if cached.rain_mm is not None else None,
                            wind_speed=float(cached.wind_speed_kmh) if cached.wind_speed_kmh is not None else None,
                            weather_code=cached.weather_code,
                            weather_condition=cached.weather_condition,
                        ),
                        daily_forecast=daily_items,
                        units=WeatherUnits(),
                    )
            except Exception as fb_err:
                logger.debug("Field weather cache fallback bypass: %s", fb_err)
        raise upstream_err

    if field:
        try:
            weather_repo = WeatherRepository(db)
            curr = field_weather_data.get("current") if isinstance(field_weather_data, dict) else getattr(field_weather_data, "current", None)
            if curr:
                temp = curr.get("temperature") if isinstance(curr, dict) else getattr(curr, "temperature", None)
                rh = curr.get("relative_humidity") if isinstance(curr, dict) else getattr(curr, "relative_humidity", None)
                precip = curr.get("precipitation") if isinstance(curr, dict) else getattr(curr, "precipitation", None)
                rain_val = curr.get("rain") if isinstance(curr, dict) else getattr(curr, "rain", None)
                wind = curr.get("wind_speed") if isinstance(curr, dict) else getattr(curr, "wind_speed", None)
                w_code = curr.get("weather_code") if isinstance(curr, dict) else getattr(curr, "weather_code", None)
                w_cond = curr.get("weather_condition") if isinstance(curr, dict) else getattr(curr, "weather_condition", None)

                await weather_repo.record_current_weather(
                    latitude=float(field.latitude),
                    longitude=float(field.longitude),
                    temperature_c=temp,
                    relative_humidity_pct=rh,
                    precipitation_mm=precip,
                    rain_mm=rain_val,
                    wind_speed_kmh=wind,
                    weather_code=w_code,
                    weather_condition=w_cond,
                    field_id=field.id,
                    provider="Open-Meteo",
                    timezone_str=timezone or "Asia/Kolkata",
                )

            # Also cache forecast days if present
            daily_items = (
                field_weather_data.get("daily_forecast") or field_weather_data.get("daily")
                if isinstance(field_weather_data, dict)
                else getattr(field_weather_data, "daily_forecast", getattr(field_weather_data, "daily", []))
            ) or []
            if daily_items:
                items = [d if isinstance(d, dict) else d.model_dump() for d in daily_items]
                await weather_repo.record_forecast_days(
                    latitude=float(field.latitude),
                    longitude=float(field.longitude),
                    forecast_items=items,
                    field_id=field.id,
                    provider="Open-Meteo",
                    timezone_str=timezone or "Asia/Kolkata",
                )
            await db.commit()
        except Exception as db_err:
            await db.rollback()
            logger.warning("Could not persist field weather observation to database: %s", db_err)

    return field_weather_data


@router.post("/predict", summary="Paddy Disease Prediction", tags=["Prediction"])
async def predict_disease(
    file: Optional[UploadFile] = File(None, description="Paddy leaf image file"),
    latitude: Optional[float] = Form(None, description="Field latitude"),
    longitude: Optional[float] = Form(None, description="Field longitude"),
    field_id: Optional[str] = Form(None, description="Field identifier"),
    question: Optional[str] = Form(None, description="Farmer advisory query"),
    language: Optional[str] = Form("en", description="Preferred response language"),
    db: AsyncSession = Depends(get_db),
):
    """
    Paddy disease classification with request validation:
    - 400: Missing image / empty file / corrupted image.
    - 415: Unsupported file extension.
    - 413: File larger than MAX_UPLOAD_SIZE_MB.
    - 503: Model checkpoint missing.
    - 500: Unexpected inference error.
    Persists successful predictions to PostgreSQL 'prediction_history' table.
    """
    # 1. Validate file presence
    if file is None or not file.filename:
        logger.warning("Prediction request rejected: No image file provided.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing uploaded image. Please provide a valid paddy leaf image file.",
        )

    # 2. Validate file extension
    filename = file.filename
    ext = Path(filename).suffix.lower()
    if ext not in config.ALLOWED_IMAGE_EXTENSIONS:
        logger.warning("Prediction request rejected: Unsupported extension '%s'", ext)
        raise UnsupportedFormatError(
            f"Unsupported file format '{ext}'. Allowed image extensions are: {', '.join(config.ALLOWED_IMAGE_EXTENSIONS)}"
        )

    try:
        # 3. Read content with size guard
        content = await file.read(config.MAX_UPLOAD_SIZE_BYTES + 1)

        if len(content) == 0:
            logger.warning("Prediction request rejected: Empty file uploaded ('%s')", filename)
            raise EmptyFileError("Uploaded image file is empty (0 bytes).")

        if len(content) > config.MAX_UPLOAD_SIZE_BYTES:
            logger.warning(
                "Prediction request rejected: File size (%d bytes) exceeds %d MB limit",
                len(content),
                config.MAX_UPLOAD_SIZE_MB,
            )
            raise FileTooLargeError(
                f"Uploaded file exceeds the maximum allowed size of {config.MAX_UPLOAD_SIZE_MB}MB."
            )

        # 4. Deep image validation with Pillow
        try:
            image_check = Image.open(io.BytesIO(content))
            image_check.verify()
        except Exception as err:
            logger.warning("Prediction request rejected: Corrupted image file '%s': %s", filename, err)
            raise CorruptedImageError("Uploaded file is corrupted or not a valid image format.") from err

        # 5. Model execution (runs in a worker thread so the server stays responsive)
        try:
            prediction_service = PredictionService()
            result = await run_in_threadpool(prediction_service.predict, content)

            if field_id:
                result["field_id"] = field_id
            if latitude is not None and longitude is not None:
                result["coordinates"] = {"latitude": latitude, "longitude": longitude}
            if question:
                result["question"] = question
            if language:
                result["language"] = language

            # Persist successful prediction to PostgreSQL prediction_history
            try:
                field_uuid = None
                if field_id:
                    field_repo = FieldRepository(db)
                    field_record = await field_repo.get_by_external_id(field_id)
                    if field_record:
                        field_uuid = field_record.id

                pred_repo = PredictionRepository(db)
                image_sha256 = hashlib.sha256(content).hexdigest()
                disease_name = result["disease"]
                pred_index = result["predicted_index"]
                conf = float(result["confidence"])
                is_healthy_flag = bool(result.get("is_healthy", False))
                top_k = result.get("top3") or result.get("top_3_predictions", [])

                pred_record = await pred_repo.create_prediction(
                    prediction_mode="image_only",
                    model_name="EfficientNet-B4",
                    model_version=config.MODEL_VERSION,
                    predicted_disease=disease_name,
                    predicted_class_index=pred_index,
                    confidence=conf,
                    is_healthy=is_healthy_flag,
                    top_k_predictions=top_k,
                    field_id=field_uuid,
                    low_confidence=conf < 0.60,
                    image_sha256=image_sha256,
                    farmer_question=question,
                    response_language=language or "en",
                    inference_latency_ms=result.get("inference_time_ms"),
                    device=config.DEVICE,
                )
                await db.commit()
                result["prediction_id"] = str(pred_record.id)
            except Exception as db_err:
                await db.rollback()
                logger.error("Failed to persist image-only prediction to database: %s", db_err, exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Inference succeeded but database persistence failed due to an internal database error.",
                ) from db_err

            return result
        except HTTPException:
            raise
        except FileNotFoundError as err:
            logger.error("AI Model checkpoint not found: %s", err)
            raise ModelUnavailableError("AI model checkpoint is currently unavailable.") from err
        except Exception as err:
            logger.error("Prediction inference failed: %s", err, exc_info=True)
            raise ModelInferenceError("An error occurred during model prediction.") from err

    finally:
        await file.close()


@router.post(
    "/predict/multimodal",
    response_model=MultimodalPredictionResponse,
    summary="Multimodal Paddy Disease Prediction",
    tags=["Prediction"],
)
async def predict_disease_multimodal(
    file: Optional[UploadFile] = File(None, description="Paddy leaf image file (parameter 'file')"),
    image: Optional[UploadFile] = File(None, description="Paddy leaf image file (parameter 'image')"),
    field_id: Optional[str] = Form(None, description="Valid field identifier (e.g. FIELD_01)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Multimodal Paddy Disease Classification fusing:
    1. Uploaded paddy leaf image (EfficientNet-B4 visual backbone -> 1792-D).
    2. Field-specific Sentinel-2 satellite time-series sequence (10 timesteps x 3 features).
    3. TemporalCrossAttentionModel for classification across 11 disease classes.

    Validation rules:
    - 400: Missing image file, empty file, corrupted image, or missing field_id.
    - 404: Unknown field_id not found in master field catalog.
    - 413: Image exceeds MAX_UPLOAD_SIZE_MB.
    - 415: Unsupported image file format.
    - 503: Multimodal or image checkpoint missing / satellite data unavailable.
    - 500: Unexpected inference error.
    Persists successful predictions to PostgreSQL 'prediction_history' table.
    """
    # 1. Resolve image file input (supports either 'file' or 'image' form field)
    target_file = file or image
    if target_file is None or not target_file.filename:
        logger.warning("Multimodal prediction rejected: No image file provided.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing uploaded image. Please provide a valid paddy leaf image file using 'file' or 'image'.",
        )

    # 2. Validate field_id presence
    if not field_id or not field_id.strip():
        logger.warning("Multimodal prediction rejected: Missing 'field_id' parameter.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required 'field_id' parameter. Please provide a valid field ID (e.g., 'FIELD_01').",
        )

    # 3. Validate file extension
    filename = target_file.filename
    ext = Path(filename).suffix.lower()
    if ext not in config.ALLOWED_IMAGE_EXTENSIONS:
        logger.warning("Multimodal prediction rejected: Unsupported extension '%s'", ext)
        raise UnsupportedFormatError(
            f"Unsupported file format '{ext}'. Allowed image extensions are: {', '.join(config.ALLOWED_IMAGE_EXTENSIONS)}"
        )

    try:
        # 4. Read content with size guard
        content = await target_file.read(config.MAX_UPLOAD_SIZE_BYTES + 1)

        if len(content) == 0:
            logger.warning("Multimodal prediction rejected: Empty file uploaded ('%s')", filename)
            raise EmptyFileError("Uploaded image file is empty (0 bytes).")

        if len(content) > config.MAX_UPLOAD_SIZE_BYTES:
            logger.warning(
                "Multimodal prediction rejected: File size (%d bytes) exceeds %d MB limit",
                len(content),
                config.MAX_UPLOAD_SIZE_MB,
            )
            raise FileTooLargeError(
                f"Uploaded file exceeds the maximum allowed size of {config.MAX_UPLOAD_SIZE_MB}MB."
            )

        # 5. Deep image validation with Pillow
        try:
            image_check = Image.open(io.BytesIO(content))
            image_check.verify()
        except Exception as err:
            logger.warning("Multimodal prediction rejected: Corrupted image file '%s': %s", filename, err)
            raise CorruptedImageError("Uploaded file is corrupted or not a valid image format.") from err

        # 6. Execute multimodal prediction in worker thread
        multimodal_service = MultimodalPredictionService()
        result = await run_in_threadpool(multimodal_service.predict, content, field_id.strip())

        # 7. Persist multimodal prediction to PostgreSQL
        try:
            field_repo = FieldRepository(db)
            field_record = await field_repo.get_by_external_id(result["field_id"])
            field_uuid = field_record.id if field_record else None

            pred_repo = PredictionRepository(db)
            image_sha256 = hashlib.sha256(content).hexdigest()
            top_pred = result["top_3_predictions"][0]
            top_disease = top_pred["disease"]
            top_index = int(top_pred["index"])
            conf = float(result["confidence"])
            top_k = [dict(p) for p in result["top_3_predictions"]]
            attention_w = result.get("temporal_attention_weights")

            pred_record = await pred_repo.create_prediction(
                prediction_mode="multimodal",
                model_name="TemporalCrossAttention",
                model_version=config.MULTIMODAL_MODEL_VERSION,
                predicted_disease=top_disease,
                predicted_class_index=top_index,
                confidence=conf,
                is_healthy=False,  # Multimodal model excludes 'normal' and 'leaf_smut'
                top_k_predictions=top_k,
                field_id=field_uuid,
                low_confidence=conf < 0.60,
                attention_weights=attention_w,
                image_sha256=image_sha256,
                response_language="en",
                device=config.DEVICE,
            )
            await db.commit()
            result["prediction_id"] = str(pred_record.id)
        except Exception as db_err:
            await db.rollback()
            logger.error("Failed to persist multimodal prediction to database: %s", db_err, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Multimodal inference succeeded but database persistence failed due to an internal database error.",
            ) from db_err

        return result

    finally:
        await target_file.close()


@router.get(
    "/predictions",
    response_model=PredictionListResponse,
    summary="List Prediction History",
    tags=["Prediction"],
)
async def list_predictions_endpoint(
    prediction_id: Optional[str] = Query(None, description="Filter by unique prediction ID (UUID)"),
    field_id: Optional[str] = Query(None, description="Filter by external field ID (e.g. FIELD_01) or UUID"),
    prediction_mode: Optional[str] = Query(None, description="Filter by mode ('image_only' or 'multimodal')"),
    disease: Optional[str] = Query(None, description="Filter by predicted disease name (e.g. 'tungro', 'sheath_blight')"),
    start_date: Optional[datetime] = Query(None, description="Filter inferences created on or after this UTC timestamp (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter inferences created on or before this UTC timestamp (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves historical disease classification inferences from PostgreSQL.
    Supports filtering by prediction_id, field, prediction_mode, disease, and date range with pagination.
    """
    if prediction_mode and prediction_mode not in ("image_only", "multimodal"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid prediction_mode '{prediction_mode}'. Allowed values: 'image_only', 'multimodal'.",
        )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date range: 'start_date' cannot be later than 'end_date'.",
        )

    pred_uuid = None
    if prediction_id:
        try:
            pred_uuid = uuid.UUID(prediction_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid prediction_id '{prediction_id}': must be a valid UUID.",
            )

    field_uuid = None
    if field_id:
        try:
            field_uuid = uuid.UUID(field_id)
        except ValueError:
            field_repo = FieldRepository(db)
            f_rec = await field_repo.get_by_external_id(field_id)
            if f_rec:
                field_uuid = f_rec.id
            else:
                return PredictionListResponse(predictions=[], total_predictions=0, page=page, page_size=page_size)

    pred_repo = PredictionRepository(db)
    skip = (page - 1) * page_size
    records, total_count = await pred_repo.list_predictions(
        prediction_id=pred_uuid,
        field_id=field_uuid,
        prediction_mode=prediction_mode,
        disease=disease,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=page_size,
    )

    items = []
    for r in records:
        items.append(
            PredictionRecordResponse(
                id=r.id,
                field_id=r.field_id,
                prediction_mode=r.prediction_mode,
                model_name=r.model_name,
                model_version=r.model_version,
                predicted_disease=r.predicted_disease,
                predicted_class_index=r.predicted_class_index,
                confidence=float(r.confidence),
                is_healthy=r.is_healthy,
                low_confidence=r.low_confidence,
                top_k_predictions=r.top_k_predictions,
                attention_weights=r.attention_weights,
                image_sha256=r.image_sha256,
                farmer_question=r.farmer_question,
                response_language=r.response_language,
                inference_latency_ms=float(r.inference_latency_ms) if r.inference_latency_ms is not None else None,
                device=r.device,
                created_at=r.created_at,
            )
        )

    return PredictionListResponse(
        predictions=items,
        total_predictions=total_count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/predictions/{prediction_id}",
    response_model=PredictionRecordResponse,
    summary="Get Specific Prediction Record",
    tags=["Prediction"],
)
async def get_prediction_by_id_endpoint(
    prediction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full details for a single diagnostic prediction inference log by UUID.
    """
    pred_repo = PredictionRepository(db)
    record = await pred_repo.get_by_id(prediction_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction record '{prediction_id}' was not found.",
        )

    return PredictionRecordResponse(
        id=record.id,
        field_id=record.field_id,
        prediction_mode=record.prediction_mode,
        model_name=record.model_name,
        model_version=record.model_version,
        predicted_disease=record.predicted_disease,
        predicted_class_index=record.predicted_class_index,
        confidence=float(record.confidence),
        is_healthy=record.is_healthy,
        low_confidence=record.low_confidence,
        top_k_predictions=record.top_k_predictions,
        attention_weights=record.attention_weights,
        image_sha256=record.image_sha256,
        farmer_question=record.farmer_question,
        response_language=record.response_language,
        inference_latency_ms=float(record.inference_latency_ms) if record.inference_latency_ms is not None else None,
        device=record.device,
        created_at=record.created_at,
    )


@router.post(
    "/reports/generate/{prediction_id}",
    response_model=ReportResponse,
    summary="Generate Disease Detection Diagnostic Report",
    tags=["Reports"],
)
async def generate_disease_report_endpoint(
    prediction_id: uuid.UUID,
    force_regenerate: bool = Query(False, description="Whether to compile a fresh report if one already exists"),
    file_format: str = Query("json", description="Report artifact format ('json', 'pdf')"),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Generates and persists a disease detection diagnostic report compiled from an existing
    PostgreSQL prediction_history record. Idempotently returns existing report if already
    generated, unless force_regenerate is explicitly True.
    """
    report_service = ReportService(db)
    report, is_new = await report_service.generate_diagnostic_report(
        prediction_id=prediction_id,
        force_regenerate=force_regenerate,
        file_format=file_format,
    )

    if response is not None:
        response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK

    return ReportResponse(
        id=report.id,
        prediction_id=report.prediction_id,
        field_id=report.field_id,
        report_type=report.report_type,
        title=report.title,
        summary=report.summary,
        status=report.status,
        file_format=report.file_format,
        file_size_bytes=report.file_size_bytes,
        report_metadata=report.report_metadata,
        generated_by=report.generated_by,
        created_at=report.created_at,
    )


@router.get(
    "/reports",
    response_model=ReportListResponse,
    summary="List Generated Reports",
    tags=["Reports"],
)
async def list_reports_endpoint(
    prediction_id: Optional[str] = Query(None, description="Filter by associated prediction UUID"),
    field_id: Optional[str] = Query(None, description="Filter by external field ID (e.g. FIELD_01) or field UUID"),
    report_type: Optional[str] = Query(None, description="Filter by category ('disease_diagnostic', 'field_health_summary', etc.)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status ('completed', 'generating', 'failed')"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a paginated list of compiled reports with optional filters.
    """
    pred_uuid = None
    if prediction_id and prediction_id.strip():
        try:
            pred_uuid = uuid.UUID(prediction_id.strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid prediction_id '{prediction_id}': must be a valid UUID.",
            )

    field_uuid = None
    if field_id and field_id.strip():
        f_val = field_id.strip()
        try:
            field_uuid = uuid.UUID(f_val)
        except ValueError:
            field_repo = FieldRepository(db)
            f_rec = await field_repo.get_by_external_id(f_val)
            if f_rec:
                field_uuid = f_rec.id
            else:
                return ReportListResponse(reports=[], total_reports=0, page=page, page_size=page_size)

    clean_report_type = report_type.strip() if report_type and report_type.strip() else None
    if clean_report_type and clean_report_type not in (
        "disease_diagnostic",
        "field_health_summary",
        "seasonal_advisory",
        "market_intelligence",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report_type '{report_type}'. Allowed values: 'disease_diagnostic', 'field_health_summary', 'seasonal_advisory', 'market_intelligence'.",
        )

    clean_status = status_filter.strip() if status_filter and status_filter.strip() else None
    if clean_status and clean_status not in ("generating", "completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{status_filter}'. Allowed values: 'generating', 'completed', 'failed'.",
        )

    report_service = ReportService(db)
    skip = (page - 1) * page_size
    records, total_count = await report_service.list_reports(
        prediction_id=pred_uuid,
        field_id=field_uuid,
        report_type=clean_report_type,
        status_filter=clean_status,
        skip=skip,
        limit=page_size,
    )

    items = [
        ReportResponse(
            id=r.id,
            prediction_id=r.prediction_id,
            field_id=r.field_id,
            report_type=r.report_type,
            title=r.title,
            summary=r.summary,
            status=r.status,
            file_format=r.file_format,
            file_size_bytes=r.file_size_bytes,
            report_metadata=r.report_metadata,
            generated_by=r.generated_by,
            created_at=r.created_at,
        )
        for r in records
    ]

    return ReportListResponse(
        reports=items,
        total_reports=total_count,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
    summary="Get Specific Report by ID",
    tags=["Reports"],
)
async def get_report_by_id_endpoint(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full details for a single report by its UUID.
    """
    report_service = ReportService(db)
    report = await report_service.get_report_by_id(report_id)

    return ReportResponse(
        id=report.id,
        prediction_id=report.prediction_id,
        field_id=report.field_id,
        report_type=report.report_type,
        title=report.title,
        summary=report.summary,
        status=report.status,
        file_format=report.file_format,
        file_size_bytes=report.file_size_bytes,
        report_metadata=report.report_metadata,
        generated_by=report.generated_by,
        created_at=report.created_at,
    )


@router.get(
    "/reports/{report_id}/download",
    summary="Download Diagnostic Report PDF",
    tags=["Reports"],
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Returns the compiled diagnostic report PDF document.",
        },
        404: {"description": "Report not found."},
        422: {"description": "Validation error (malformed report_id UUID)."},
    },
)
async def download_report_pdf_endpoint(
    report_id: uuid.UUID,
    regenerate: bool = Query(False, description="Whether to force re-compiling the PDF artifact from database metadata"),
    db: AsyncSession = Depends(get_db),
):
    """
    Downloads the compiled PDF diagnostic report for a specific report UUID.
    Returns HTTP 404 if the report does not exist.
    Guarantees zero leakage of server filesystem paths, raw GPS coordinates, or database credentials.
    """
    report_service = ReportService(db)
    pdf_bytes, filename = await report_service.get_pdf_artifact_bytes(report_id, force_regenerate=regenerate)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "X-Report-Id": str(report_id),
        },
    )


@router.post(
    "/explain/gradcam",
    response_model=GradCAMResponse,
    summary="Generate Grad-CAM Visual Explanation",
    tags=["Explanation"],
)
async def explain_gradcam(
    file: Optional[UploadFile] = File(None, description="Paddy leaf image file (parameter 'file')"),
    image: Optional[UploadFile] = File(None, description="Paddy leaf image file (parameter 'image')"),
    target_class: Optional[str] = Form(None, description="Target disease class name to explain (defaults to top predicted class)"),
    target_index: Optional[int] = Form(None, description="Target disease class index (0-12) to explain"),
    alpha: Optional[float] = Form(0.5, description="Overlay blending opacity [0.1 - 0.9]"),
    response_format: Optional[str] = Form("json", description="Response format: 'json' (default) or 'image'"),
):
    """
    Computes Gradient-weighted Class Activation Mapping (Grad-CAM)
    on the final convolutional layer (features[8]) of the trained EfficientNet-B4 model.

    Highlights image regions that positively contributed to the target disease class score.
    Returns a structured JSON response containing the base64 data URI overlay,
    saved visualization URL, and scientific interpretation disclaimers.
    Optionally returns raw JPEG image when response_format='image'.
    """
    # 1. Resolve image file input
    target_file = file or image
    if target_file is None or not target_file.filename:
        logger.warning("Grad-CAM request rejected: No image file provided.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing uploaded image. Please provide a valid paddy leaf image file using 'file' or 'image'.",
        )

    # 2. Validate file extension
    filename = target_file.filename
    ext = Path(filename).suffix.lower()
    if ext not in config.ALLOWED_IMAGE_EXTENSIONS:
        logger.warning("Grad-CAM request rejected: Unsupported extension '%s'", ext)
        raise UnsupportedFormatError(
            f"Unsupported file format '{ext}'. Allowed image extensions are: {', '.join(config.ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # 3. Validate target_class / target_index if provided
    gradcam_service = GradCAMService()
    try:
        gradcam_service.validate_target_class(target_class, target_index)
    except ValueError as val_err:
        logger.warning("Grad-CAM request rejected: %s", val_err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err)) from val_err

    try:
        # 4. Read content with size guard
        content = await target_file.read(config.MAX_UPLOAD_SIZE_BYTES + 1)

        if len(content) == 0:
            logger.warning("Grad-CAM request rejected: Empty file uploaded ('%s')", filename)
            raise EmptyFileError("Uploaded image file is empty (0 bytes).")

        if len(content) > config.MAX_UPLOAD_SIZE_BYTES:
            logger.warning(
                "Grad-CAM request rejected: File size (%d bytes) exceeds %d MB limit",
                len(content),
                config.MAX_UPLOAD_SIZE_MB,
            )
            raise FileTooLargeError(
                f"Uploaded file exceeds the maximum allowed size of {config.MAX_UPLOAD_SIZE_MB}MB."
            )

        # 5. Deep image validation with Pillow
        try:
            image_check = Image.open(io.BytesIO(content))
            image_check.verify()
        except Exception as err:
            logger.warning("Grad-CAM request rejected: Corrupted image file '%s': %s", filename, err)
            raise CorruptedImageError("Uploaded file is corrupted or not a valid image format.") from err

        # 6. Execute Grad-CAM computation in worker thread
        result = await run_in_threadpool(
            gradcam_service.generate_gradcam,
            content,
            target_class=target_class,
            target_index=target_index,
            alpha=alpha or 0.5,
        )

        # 7. Return raw image if requested, otherwise JSON response
        if response_format and response_format.lower() == "image":
            return Response(
                content=result["raw_bytes"],
                media_type="image/jpeg",
                headers={
                    "X-Predicted-Class": result["predicted_class"],
                    "X-Target-Class": result["target_class"],
                    "X-Confidence": str(result["confidence"]),
                },
            )

        # Omit raw_bytes from JSON payload
        result.pop("raw_bytes", None)
        return result

    finally:
        await target_file.close()


@router.post(
    "/explain/shap",
    response_model=SHAPExplanationResponse,
    summary="Temporal Multimodal SHAP Explanation",
    tags=["Explainability"],
)
async def explain_shap(
    file: Optional[UploadFile] = File(None, description="Uploaded paddy leaf image (file field)"),
    image: Optional[UploadFile] = File(None, description="Uploaded paddy leaf image (alias parameter)"),
    field_id: str = Form(..., description="Canonical field identifier (e.g. FIELD_01)"),
    target_class: Optional[str] = Form(None, description="Optional target disease class to explain"),
    target_index: Optional[int] = Form(None, description="Optional target disease class index to explain"),
    nsamples: Optional[int] = Form(None, description="Optional background evaluation sample count (default 100)"),
    seed: Optional[int] = Form(42, description="Optional random seed for deterministic background evaluation (default 42)"),
):
    """
    Computes class-specific SHAP feature attributions for the multimodal cross-attention classifier.
    Explains the temporal Sentinel-2 satellite time-series features (NDVI, NDRE, GNDVI across 10 timesteps)
    conditioned on the uploaded leaf image's deep visual embedding.
    """
    target_file = file or image
    if not target_file:
        logger.warning("SHAP explanation rejected: No image file provided.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing uploaded image. Please provide a valid paddy leaf image file using 'file' or 'image'.",
        )

    # 1. Filename & Extension Verification
    filename = target_file.filename or ""
    file_ext = Path(filename).suffix.lower()
    if file_ext not in config.ALLOWED_IMAGE_EXTENSIONS:
        logger.warning("SHAP explanation rejected: Unsupported extension '%s'", file_ext)
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file format '{file_ext}'. "
                f"Allowed image extensions are: {', '.join(config.ALLOWED_IMAGE_EXTENSIONS)}"
            ),
        )

    # 2. Field ID parameter validation
    clean_field_id = str(field_id).strip().upper()
    if not clean_field_id:
        logger.warning("SHAP explanation rejected: Empty field_id.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field_id parameter.",
        )

    try:
        # 3. Read image bytes and validate payload size
        content = await target_file.read()
        if len(content) == 0:
            logger.warning("SHAP explanation rejected: Empty file uploaded ('%s')", filename)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded image file is empty (0 bytes).",
            )

        if len(content) > config.MAX_UPLOAD_SIZE_BYTES:
            logger.warning(
                "SHAP explanation rejected: File '%s' exceeded size limit (%d bytes)",
                filename,
                len(content),
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded image exceeds maximum allowable limit of {config.MAX_UPLOAD_SIZE_MB}MB.",
            )

        # 4. Integrity check via PIL
        try:
            with Image.open(io.BytesIO(content)) as img_obj:
                img_obj.verify()
        except Exception as err:
            logger.warning("SHAP explanation rejected: Corrupted image file '%s': %s", filename, err)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is corrupted or not a valid image format.",
            )

        # 5. Compute SHAP explanations in threadpool
        try:
            result = await run_in_threadpool(
                shap_service.explain_multimodal,
                content,
                field_id=clean_field_id,
                target_class=target_class,
                target_index=target_index,
                nsamples=nsamples,
                seed=seed,
            )
            return result
        except ValueError as val_err:
            logger.warning("SHAP explanation validation error: %s", val_err)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(val_err),
            )
        except FieldNotFoundError as fnf_err:
            logger.warning("SHAP explanation field not found: %s", fnf_err)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(fnf_err),
            )
        except SatelliteDataUnavailableError as sdu_err:
            logger.error("SHAP explanation satellite data unavailable: %s", sdu_err)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(sdu_err),
            )
        except ModelUnavailableError as mu_err:
            logger.error("SHAP explanation model unavailable: %s", mu_err)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(mu_err),
            )
        except Exception as exc:
            logger.exception("Unexpected error computing SHAP explanation: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal server error occurred while computing the SHAP explanation.",
            )


    finally:
        await target_file.close()


# =====================================================================
# Market Prices Endpoints (STEP 11F.10)
# =====================================================================

@router.get(
    "/market/prices",
    response_model=MarketPriceListResponse,
    summary="List Agricultural Mandi Market Prices",
    tags=["Market Prices"],
)
async def list_market_prices(
    district: Optional[str] = Query(None, description="Filter by administrative district (case-insensitive)"),
    commodity: Optional[str] = Query(None, description="Filter by commodity name (e.g. 'Paddy (Dhan)')"),
    variety: Optional[str] = Query(None, description="Filter by crop variety (e.g. 'Common', 'BPT 5204')"),
    state: Optional[str] = Query(None, description="Filter by state (e.g. 'Andhra Pradesh')"),
    force_live: bool = Query(False, description="Bypass cache and attempt live upstream retrieval"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return (1-200)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves official wholesale mandi commodity spot prices with intelligent live/local fallback.
    - If fresh local records exist, returns them immediately (data_source='database_cache').
    - If local records are missing or stale, queries Data.gov.in (if API key is configured).
    - Caches upstream quotes atomically in PostgreSQL.
    - Falls back to available local records if upstream is unavailable (data_source='database_stale').
    - Returns valid empty response if no records match or the table is empty.
    """
    try:
        svc = MarketService.get_instance()
        result = await svc.get_prices_with_fallback(
            session=db,
            state=state,
            district=district,
            commodity=commodity,
            variety=variety,
            skip=skip,
            limit=limit,
            force_live=force_live,
        )
        return MarketPriceListResponse(
            items=[MarketPriceItem.model_validate(r) for r in result["items"]],
            total=result["total"],
            skip=result["skip"],
            limit=result["limit"],
            data_source=result["data_source"],
            is_stale=result["is_stale"],
            freshness_date=result["freshness_date"],
        )
    except Exception as exc:
        logger.error("Error retrieving market prices: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while querying market prices.",
        )


@router.get(
    "/market/prices/latest",
    response_model=MarketPriceListResponse,
    summary="Get Latest Agricultural Mandi Prices",
    tags=["Market Prices"],
)
async def get_latest_market_prices(
    district: Optional[str] = Query(None, description="Filter by administrative district"),
    commodity: Optional[str] = Query(None, description="Filter by commodity name"),
    state: Optional[str] = Query(None, description="Filter by state"),
    force_live: bool = Query(False, description="Bypass cache and attempt live upstream retrieval"),
    limit: int = Query(20, ge=1, le=100, description="Number of latest price quotations to return (1-100)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the most recent agricultural market spot prices with live/local fallback.
    Useful for dashboard feeds and farmer advisory benchmarks.
    """
    try:
        svc = MarketService.get_instance()
        result = await svc.get_prices_with_fallback(
            session=db,
            state=state,
            district=district,
            commodity=commodity,
            variety=None,
            skip=0,
            limit=limit,
            force_live=force_live,
        )
        return MarketPriceListResponse(
            items=[MarketPriceItem.model_validate(r) for r in result["items"]],
            total=result["total"],
            skip=0,
            limit=limit,
            data_source=result["data_source"],
            is_stale=result["is_stale"],
            freshness_date=result["freshness_date"],
        )
    except Exception as exc:
        logger.error("Error retrieving latest market prices: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while querying latest market prices.",
        )


@router.post(
    "/market/sync",
    response_model=MarketSyncResponse,
    summary="Synchronize Live Agricultural Mandi Prices",
    tags=["Market Prices"],
)
async def sync_live_market_prices(
    state: str = Query("Andhra Pradesh", description="Administrative state name"),
    district: Optional[str] = Query(None, description="Optional administrative district filter (e.g. 'Chittoor', 'Nellore')"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of upstream records to sync (1-200)"),
    offset: int = Query(0, ge=0, description="Offset for upstream records"),
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronizes genuine live agricultural mandi spot prices from the official Data.gov.in (Agmarknet) API.
    - Requires DATAGOVIN_API_KEY configured in backend environment.
    - Validates schema, price constraints, and arrival dates.
    - Atomically upserts valid records into PostgreSQL via MarketPriceRepository.
    - Never fabricates synthetic prices if credentials or service is unavailable.
    """
    if not config.MARKET_SERVICE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market price synchronization is disabled in configuration.",
        )

    if not config.DATAGOVIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live market synchronization is unavailable: Data.gov.in API key is not configured. Please set DATAGOVIN_API_KEY in the backend environment.",
        )

    market_svc = MarketService.get_instance()
    try:
        sync_result = await run_in_threadpool(
            market_svc.fetch_live_paddy_prices_detailed,
            district=district,
            state=state,
            limit=limit,
            offset=offset,
        )
    except MarketApiKeyMissingError as key_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Live market synchronization is unavailable: {key_err.message}",
        )
    except MarketServiceUnavailableError as unavail_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Upstream market price provider unavailable: {unavail_err.message}",
        )
    except MarketProviderError as prov_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream market price provider error: {prov_err.message}",
        )
    except MarketParsingError as parse_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse upstream market response: {parse_err.message}",
        )
    except Exception as exc:
        logger.exception("Unexpected error during live market sync: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during market price synchronization.",
        )

    try:
        repo = MarketPriceRepository(db)
        persisted = await repo.upsert_prices(sync_result["valid_prices"])
        await db.commit()
    except Exception as db_exc:
        await db.rollback()
        logger.error("Failed to persist synced market prices to database: %s", db_exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while saving synchronized market prices.",
        )

    return MarketSyncResponse(
        status="success",
        provider="Data.gov.in (Agmarknet)",
        upstream_status_code=sync_result.get("upstream_status_code", 200),
        records_retrieved=sync_result["raw_retrieved"],
        records_accepted=sync_result["records_accepted"],
        records_rejected=sync_result["records_rejected"],
        records_persisted=persisted,
        state=state,
        district=district,
        synced_at=datetime.now(timezone.utc),
        detail=f"Successfully synced {persisted} authentic market price quotations into database.",
    )


# =====================================================================
# Market Price Analytics & Trends Endpoints (STEP 11G.4)
# =====================================================================

@router.get(
    "/market/analytics/summary",
    response_model=MarketSummaryResponse,
    summary="Get Mandi Price Statistical Summary",
    tags=["Market Prices", "Market Analytics"],
)
async def get_market_summary(
    state: Optional[str] = Query(None, description="Administrative state filter (e.g. 'Andhra Pradesh')"),
    district: Optional[str] = Query(None, description="Administrative district filter (e.g. 'Chittoor')"),
    commodity: Optional[str] = Query("Paddy (Dhan)", description="Standardized commodity name"),
    variety: Optional[str] = Query(None, description="Crop variety or cultivar filter"),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes statistical aggregate indicators (average, min, max modal prices,
    transaction range, observation count, and latest quotation date) across genuine
    persisted database records.
    Never fabricates missing data; clearly distinguishes no data from zero.
    """
    try:
        repo = MarketPriceRepository(db)
        data = await repo.get_market_summary(
            state=state,
            district=district,
            commodity=commodity,
            variety=variety,
        )
        return MarketSummaryResponse.model_validate(data)
    except Exception as exc:
        logger.error("Error computing market summary analytics: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while computing market summary analytics.",
        )


@router.get(
    "/market/analytics/trends",
    response_model=MarketTrendsResponse,
    summary="Get Mandi Price Historical Trends",
    tags=["Market Prices", "Market Analytics"],
)
async def get_market_trends(
    days: int = Query(7, ge=1, le=90, description="Analysis historical window in days (1-90, default 7)"),
    state: Optional[str] = Query(None, description="Administrative state filter"),
    district: Optional[str] = Query(None, description="Administrative district filter"),
    commodity: Optional[str] = Query("Paddy (Dhan)", description="Standardized commodity name"),
    variety: Optional[str] = Query(None, description="Crop variety filter"),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculates historical daily price points and net trend trajectory over the requested window.
    Strictly returns trend_direction='insufficient_data' if fewer than 2 distinct observation dates exist.
    Never fabricates synthetic price points.
    """
    try:
        repo = MarketPriceRepository(db)
        data = await repo.get_daily_trends(
            days=days,
            state=state,
            district=district,
            commodity=commodity,
            variety=variety,
        )
        return MarketTrendsResponse.model_validate(data)
    except Exception as exc:
        logger.error("Error computing market trends: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while computing market trends.",
        )


@router.get(
    "/market/analytics/districts",
    response_model=DistrictAnalyticsResponse,
    summary="Get District-Level Mandi Price Benchmarks",
    tags=["Market Prices", "Market Analytics"],
)
async def get_district_analytics(
    days: int = Query(30, ge=1, le=90, description="Analysis time window in days (1-90, default 30)"),
    state: Optional[str] = Query("Andhra Pradesh", description="Administrative state name"),
    commodity: Optional[str] = Query("Paddy (Dhan)", description="Standardized commodity name"),
    variety: Optional[str] = Query(None, description="Crop variety filter"),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregates district-level modal prices and calculates differentials against state averages.
    Ranks districts from highest to lowest price and computes the regional price spread.
    """
    try:
        repo = MarketPriceRepository(db)
        data = await repo.get_district_benchmarks(
            days=days,
            state=state,
            commodity=commodity,
            variety=variety,
        )
        return DistrictAnalyticsResponse.model_validate(data)
    except Exception as exc:
        logger.error("Error computing district benchmarks: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while computing district benchmarks.",
        )


@router.get(
    "/market/analytics/varieties",
    response_model=VarietyAnalyticsResponse,
    summary="Get Variety-Level Mandi Price Benchmarks",
    tags=["Market Prices", "Market Analytics"],
)
async def get_variety_analytics(
    days: int = Query(30, ge=1, le=90, description="Analysis time window in days (1-90, default 30)"),
    state: Optional[str] = Query("Andhra Pradesh", description="Administrative state name"),
    district: Optional[str] = Query(None, description="Administrative district filter"),
    commodity: Optional[str] = Query("Paddy (Dhan)", description="Standardized commodity name"),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregates cultivar/variety modal prices and identifies premium and standard benchmark varieties.
    Rankings are ordered by average modal price descending.
    """
    try:
        repo = MarketPriceRepository(db)
        data = await repo.get_variety_benchmarks(
            days=days,
            state=state,
            district=district,
            commodity=commodity,
        )
        return VarietyAnalyticsResponse.model_validate(data)
    except Exception as exc:
        logger.error("Error computing variety benchmarks: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while computing variety benchmarks.",
        )


# =====================================================================
# Buyers & Millers Endpoints (STEP 11F.10)
# =====================================================================

@router.get(
    "/buyers",
    response_model=BuyerListResponse,
    summary="List Verified Grain Buyers and Millers",
    tags=["Buyers"],
)
async def list_buyers(
    district: Optional[str] = Query(None, description="Filter by district (case-insensitive)"),
    buyer_type: Optional[str] = Query(None, description="Filter by buyer category: 'mill', 'fpo', 'government_agency', 'wholesaler', 'trader'"),
    state: Optional[str] = Query(None, description="Filter by state (case-insensitive)"),
    verification_status: Optional[str] = Query(None, description="Filter by status: 'verified', 'pending', 'unverified'"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return (1-200)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves verified wholesale grain buyers, custom milling rice (CMR) millers,
    Farmer Producer Organizations (FPOs), and government procurement agencies.
    Results are deterministically ordered by business name ascending and ID ascending.
    Returns valid empty response if no records match or the table is empty.
    """
    try:
        repo = BuyerRepository(db)
        records, total = await repo.list_buyers(
            district=district,
            buyer_type=buyer_type,
            state=state,
            verification_status=verification_status,
            skip=skip,
            limit=limit,
        )
        return BuyerListResponse(
            items=[BuyerItem.model_validate(r) for r in records],
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as exc:
        logger.error("Error retrieving buyers: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while querying buyers directory.",
        )


@router.get(
    "/buyers/nearby",
    response_model=BuyerNearbyResponse,
    summary="Find Nearest Grain Buyers by GPS Coordinates",
    tags=["Buyers"],
)
async def list_nearby_buyers(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Farmer latitude coordinate in WGS84 decimal degrees (-90 to +90)"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Farmer longitude coordinate in WGS84 decimal degrees (-180 to +180)"),
    radius_km: Optional[float] = Query(None, gt=0.0, le=500.0, description="Optional maximum search radius in kilometers (positive, max 500km)"),
    district: Optional[str] = Query(None, description="Filter by district (case-insensitive)"),
    buyer_type: Optional[str] = Query(None, description="Filter by buyer category: 'mill', 'fpo', 'government_agency', 'wholesaler', 'trader'"),
    state: Optional[str] = Query(None, description="Filter by state (case-insensitive)"),
    verification_status: Optional[str] = Query(None, description="Filter by status: 'verified', 'pending', 'unverified'"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return (1-200)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Ranks verified grain buyers, rice mills, and procurement agencies by straight-line geographical
    distance (great-circle Haversine formula) from the provided farmer GPS coordinates.
    Only active buyers with verified non-null coordinates are included in proximity ranking.
    Buyers without coordinates are excluded.
    Results are deterministically ordered by distance ascending, then business name, then buyer ID.
    """
    try:
        repo = BuyerRepository(db)
        scored_records, total = await repo.list_nearby_buyers(
            farmer_lat=lat,
            farmer_lon=lon,
            radius_km=radius_km,
            district=district,
            buyer_type=buyer_type,
            state=state,
            verification_status=verification_status,
            skip=skip,
            limit=limit,
        )

        nearby_items = []
        for buyer, dist in scored_records:
            item_dict = BuyerItem.model_validate(buyer).model_dump()
            item_dict["distance_km"] = dist
            nearby_items.append(BuyerNearbyItem(**item_dict))

        return BuyerNearbyResponse(
            items=nearby_items,
            total=total,
            skip=skip,
            limit=limit,
            farmer_latitude=lat,
            farmer_longitude=lon,
            search_radius_km=radius_km,
        )
    except Exception as exc:
        logger.error("Error retrieving nearby buyers: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while calculating nearby buyers.",
        )


@router.get(
    "/buyers/{buyer_id}",
    response_model=BuyerItem,
    summary="Get Specific Buyer Details",
    tags=["Buyers"],
)
async def get_buyer_by_id(
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves verified profile details for a specific agricultural buyer or miller by UUID.
    Returns HTTP 404 if the buyer is not found in the directory.
    Returns HTTP 422 if an invalid UUID format is provided.
    """
    try:
        repo = BuyerRepository(db)
        buyer = await repo.get_by_id(buyer_id)
        if not buyer or not buyer.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Buyer '{buyer_id}' was not found in the directory.",
            )
        return BuyerItem.model_validate(buyer)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error retrieving buyer '%s': %s", buyer_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal database error occurred while retrieving buyer profile.",
        )