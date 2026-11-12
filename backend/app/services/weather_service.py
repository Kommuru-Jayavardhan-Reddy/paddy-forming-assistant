"""
Paddy Farming Assistant - Weather Service (STEP 11E.2)
Fetches and structures real atmospheric weather and multi-day agro-forecasts
from Open-Meteo for verified field coordinates across Andhra Pradesh.
Operates without API keys, handles network failures gracefully,
and preserves strict scientific data integrity without fabricating synthetic values.
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app import config
from app.exceptions import (
    InvalidCoordinatesError,
    WeatherServiceDisabledError,
    WeatherServiceUnavailableError,
    WeatherProviderError,
    WeatherParsingError,
)

logger = logging.getLogger(__name__)

# World Meteorological Organization (WMO) Weather Code Descriptions
# Standardized interpretations for agricultural and public advisories
WMO_WEATHER_CODE_DESCRIPTIONS: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _safe_float(val: Any) -> Optional[float]:
    """Safely converts input to float; returns None for null, nan, or inf."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 2)
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any) -> Optional[int]:
    """Safely converts input to integer; returns None for null or invalid types."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


class WeatherService:
    """
    Dedicated client service for querying real-time atmospheric measurements
    and short-term forecasts from Open-Meteo.
    """

    _instance: Optional["WeatherService"] = None

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url or config.WEATHER_API_BASE_URL
        self.timeout = timeout if timeout is not None else config.WEATHER_REQUEST_TIMEOUT_SECONDS
        self.provider = config.WEATHER_PROVIDER

        if session is not None:
            self.session = session
        else:
            # Configure reusable HTTP session with connection pooling
            self.session = requests.Session()
            retry_strategy = Retry(
                total=2,
                backoff_factor=0.3,
                status_forcelist=[502, 503, 504],
                allowed_methods=["GET"],
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=5, pool_maxsize=10)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

    @classmethod
    def get_instance(cls) -> "WeatherService":
        """Singleton accessor for application-wide client reuse."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Resets the singleton instance (primarily for testing and mocking)."""
        if cls._instance is not None:
            try:
                cls._instance.close()
            except Exception:
                pass
            cls._instance = None

    def close(self) -> None:
        """Closes the underlying requests session."""
        if self.session is not None:
            self.session.close()

    def validate_coordinates(self, latitude: Any, longitude: Any) -> Tuple[float, float]:
        """
        Validates latitude and longitude boundaries according to WGS84 standards.
        Latitude must be between -90.0 and 90.0.
        Longitude must be between -180.0 and 180.0.
        Raises InvalidCoordinatesError if validation fails.
        """
        if latitude is None or longitude is None:
            raise InvalidCoordinatesError("Latitude and longitude coordinates are required.")

        try:
            lat = float(latitude)
        except (ValueError, TypeError):
            raise InvalidCoordinatesError(f"Invalid latitude value: '{latitude}' must be numeric.")

        try:
            lon = float(longitude)
        except (ValueError, TypeError):
            raise InvalidCoordinatesError(f"Invalid longitude value: '{longitude}' must be numeric.")

        if math.isnan(lat) or math.isinf(lat):
            raise InvalidCoordinatesError("Latitude cannot be NaN or Infinite.")

        if math.isnan(lon) or math.isinf(lon):
            raise InvalidCoordinatesError("Longitude cannot be NaN or Infinite.")

        if not (-90.0 <= lat <= 90.0):
            raise InvalidCoordinatesError(
                f"Latitude {lat} is out of valid range [-90.0, 90.0]."
            )

        if not (-180.0 <= lon <= 180.0):
            raise InvalidCoordinatesError(
                f"Longitude {lon} is out of valid range [-180.0, 180.0]."
            )

        return lat, lon

    def get_weather(
        self,
        latitude: Any,
        longitude: Any,
        timezone: Optional[str] = None,
        forecast_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Queries Open-Meteo for real-time weather and multi-day agro-forecast.
        Validates coordinates, checks service enablement, and handles provider failures safely.
        """
        if not config.WEATHER_SERVICE_ENABLED:
            logger.warning("Weather service query rejected: service is disabled in configuration.")
            raise WeatherServiceDisabledError()

        lat, lon = self.validate_coordinates(latitude, longitude)
        tz = timezone or config.WEATHER_DEFAULT_TIMEZONE
        safe_forecast_days = max(1, min(16, int(forecast_days)))

        # Define metric parameters for Indian agro-climatic context
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,wind_speed_10m_max,weather_code",
            "forecast_days": safe_forecast_days,
            "timezone": tz,
        }

        logger.debug(
            "Requesting weather data from %s for coordinates (lat=%.6f, lon=%.6f)",
            self.base_url,
            lat,
            lon,
        )

        try:
            response = self.session.get(self.base_url, params=params, timeout=self.timeout)
        except requests.exceptions.Timeout as e:
            logger.error("Weather service request timed out after %.1fs: %s", self.timeout, e)
            raise WeatherServiceUnavailableError(
                f"Weather provider request timed out after {self.timeout} seconds."
            )
        except requests.exceptions.ConnectionError as e:
            logger.error("Weather service network connection failed: %s", e)
            raise WeatherServiceUnavailableError(
                "Unable to connect to weather provider network. Service is temporarily unreachable."
            )
        except requests.exceptions.RequestException as e:
            logger.error("Unexpected requests exception encountered: %s", e)
            raise WeatherServiceUnavailableError(
                "A network communication error occurred with the weather service provider."
            )

        # Handle HTTP status codes
        if response.status_code >= 500:
            logger.error("Weather provider returned upstream server error: HTTP %d", response.status_code)
            raise WeatherServiceUnavailableError(
                f"Weather service provider encountered an internal server error (HTTP {response.status_code})."
            )

        if response.status_code >= 400:
            logger.error("Weather provider rejected request: HTTP %d - %s", response.status_code, response.text)
            raise WeatherProviderError(
                f"Weather provider rejected the request with status code {response.status_code}."
            )

        # Parse JSON payload
        try:
            payload = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError) as e:
            logger.error("Weather provider returned invalid JSON: %s", e)
            raise WeatherParsingError("Weather service provider returned a malformed, non-JSON response.")

        if not isinstance(payload, dict):
            logger.error("Weather provider returned non-dict JSON structure: %s", type(payload))
            raise WeatherParsingError("Weather provider returned an unexpected payload structure.")

        return self._parse_weather_payload(payload, requested_lat=lat, requested_lon=lon)

    def _parse_weather_payload(
        self,
        payload: Dict[str, Any],
        requested_lat: float,
        requested_lon: float,
    ) -> Dict[str, Any]:
        """
        Parses real Open-Meteo JSON payload into standard application domain schema.
        Preserves strictly returned fields without inventing unmeasured values.
        """
        # Coordinate and metadata extraction
        resp_lat = _safe_float(payload.get("latitude"))
        resp_lon = _safe_float(payload.get("longitude"))
        elevation = _safe_float(payload.get("elevation"))
        timezone = payload.get("timezone")
        tz_abbr = payload.get("timezone_abbreviation")
        utc_offset_seconds = _safe_int(payload.get("utc_offset_seconds"))

        # Extract current observation
        current_data = payload.get("current")
        current_units = payload.get("current_units", {})
        parsed_current: Optional[Dict[str, Any]] = None

        if isinstance(current_data, dict):
            w_code = _safe_int(current_data.get("weather_code"))
            condition_desc = WMO_WEATHER_CODE_DESCRIPTIONS.get(w_code) if w_code is not None else None

            parsed_current = {
                "time": current_data.get("time"),
                "interval_seconds": _safe_int(current_data.get("interval")),
                "temperature": _safe_float(current_data.get("temperature_2m")),
                "temperature_unit": current_units.get("temperature_2m", "°C"),
                "relative_humidity": _safe_float(current_data.get("relative_humidity_2m")),
                "relative_humidity_unit": current_units.get("relative_humidity_2m", "%"),
                "precipitation": _safe_float(current_data.get("precipitation")),
                "precipitation_unit": current_units.get("precipitation", "mm"),
                "rain": _safe_float(current_data.get("rain")),
                "rain_unit": current_units.get("rain", "mm"),
                "wind_speed": _safe_float(current_data.get("wind_speed_10m")),
                "wind_speed_unit": current_units.get("wind_speed_10m", "km/h"),
                "weather_code": w_code,
                "weather_condition": condition_desc,
            }

        # Extract daily forecast summaries
        daily_data = payload.get("daily")
        daily_units = payload.get("daily_units", {})
        parsed_forecast: List[Dict[str, Any]] = []

        if isinstance(daily_data, dict):
            dates = daily_data.get("time", [])
            t_max_list = daily_data.get("temperature_2m_max", [])
            t_min_list = daily_data.get("temperature_2m_min", [])
            precip_list = daily_data.get("precipitation_sum", [])
            rain_list = daily_data.get("rain_sum", [])
            wind_list = daily_data.get("wind_speed_10m_max", [])
            code_list = daily_data.get("weather_code", [])

            if isinstance(dates, list):
                for i, date_str in enumerate(dates):
                    t_max = _safe_float(t_max_list[i]) if i < len(t_max_list) else None
                    t_min = _safe_float(t_min_list[i]) if i < len(t_min_list) else None
                    precip_sum = _safe_float(precip_list[i]) if i < len(precip_list) else None
                    rain_sum = _safe_float(rain_list[i]) if i < len(rain_list) else None
                    wind_max = _safe_float(wind_list[i]) if i < len(wind_list) else None
                    day_code = _safe_int(code_list[i]) if i < len(code_list) else None
                    day_cond = WMO_WEATHER_CODE_DESCRIPTIONS.get(day_code) if day_code is not None else None

                    parsed_forecast.append({
                        "date": date_str,
                        "temperature_max": t_max,
                        "temperature_min": t_min,
                        "temperature_unit": daily_units.get("temperature_2m_max", "°C"),
                        "precipitation_sum": precip_sum,
                        "precipitation_unit": daily_units.get("precipitation_sum", "mm"),
                        "rain_sum": rain_sum,
                        "rain_sum_unit": daily_units.get("rain_sum", "mm"),
                        "wind_speed_max": wind_max,
                        "wind_speed_unit": daily_units.get("wind_speed_10m_max", "km/h"),
                        "weather_code": day_code,
                        "weather_condition": day_cond,
                    })

        return {
            "provider": self.provider,
            "coordinates": {
                "latitude": resp_lat if resp_lat is not None else requested_lat,
                "longitude": resp_lon if resp_lon is not None else requested_lon,
                "elevation": elevation,
            },
            "timezone": timezone,
            "timezone_abbreviation": tz_abbr,
            "utc_offset_seconds": utc_offset_seconds,
            "current": parsed_current,
            "daily_forecast": parsed_forecast,
            "units": {
                "temperature": "°C",
                "relative_humidity": "%",
                "precipitation": "mm",
                "wind_speed": "km/h",
            },
        }

    def get_current_weather(
        self,
        latitude: Any,
        longitude: Any,
        timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves strictly the current weather conditions for the specified coordinates.
        """
        full_weather = self.get_weather(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            forecast_days=1,
        )
        return {
            "provider": full_weather["provider"],
            "coordinates": full_weather["coordinates"],
            "timezone": full_weather["timezone"],
            "current": full_weather["current"],
            "units": full_weather["units"],
        }

    def get_forecast(
        self,
        latitude: Any,
        longitude: Any,
        forecast_days: int = 7,
        timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves multi-day daily weather forecast summaries for the specified coordinates.
        """
        full_weather = self.get_weather(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            forecast_days=forecast_days,
        )
        return {
            "provider": full_weather["provider"],
            "coordinates": full_weather["coordinates"],
            "timezone": full_weather["timezone"],
            "daily_forecast": full_weather["daily_forecast"],
            "units": full_weather["units"],
        }

    def get_weather_for_field(
        self,
        field_id: str,
        forecast_days: int = 7,
        timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resolves authoritative coordinates for a known field ID and retrieves real atmospheric
        data and multi-day agro-forecast from Open-Meteo.
        Raises FieldNotFoundError (HTTP 404) if field_id is unknown.
        Raises InvalidCoordinatesError (HTTP 400) if field coordinates are invalid or missing.
        """
        from app.services.field_mapping import FieldMappingService
        field_service = FieldMappingService.get_instance()
        lat, lon = field_service.get_field_coordinates(field_id)

        field_info = field_service.get_field(field_id)
        canonical_fid = field_info["field_id"] if field_info else field_id.strip().upper()
        clean_fid = field_info.get("clean_field_id") if field_info else None

        weather_data = self.get_weather(
            latitude=lat,
            longitude=lon,
            timezone=timezone,
            forecast_days=forecast_days,
        )

        return {
            "field_id": canonical_fid,
            "requested_field_id": field_id,
            "clean_field_id": clean_fid,
            "provider": weather_data["provider"],
            "coordinates": {
                "latitude": lat,
                "longitude": lon,
                "elevation": weather_data["coordinates"].get("elevation"),
            },
            "timezone": weather_data["timezone"],
            "timezone_abbreviation": weather_data.get("timezone_abbreviation"),
            "utc_offset_seconds": weather_data.get("utc_offset_seconds"),
            "current": weather_data["current"],
            "daily_forecast": weather_data["daily_forecast"],
            "units": weather_data["units"],
        }

    def get_current_weather_for_field(
        self,
        field_id: str,
        timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves strictly current weather observations for a specific field ID.
        """
        full_result = self.get_weather_for_field(
            field_id=field_id,
            forecast_days=1,
            timezone=timezone,
        )
        return {
            "field_id": full_result["field_id"],
            "requested_field_id": full_result["requested_field_id"],
            "clean_field_id": full_result.get("clean_field_id"),
            "provider": full_result["provider"],
            "coordinates": full_result["coordinates"],
            "timezone": full_result["timezone"],
            "current": full_result["current"],
            "units": full_result["units"],
        }

    def get_forecast_for_field(
        self,
        field_id: str,
        forecast_days: int = 7,
        timezone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves multi-day daily weather forecast summaries for a specific field ID.
        """
        full_result = self.get_weather_for_field(
            field_id=field_id,
            forecast_days=forecast_days,
            timezone=timezone,
        )
        return {
            "field_id": full_result["field_id"],
            "requested_field_id": full_result["requested_field_id"],
            "clean_field_id": full_result.get("clean_field_id"),
            "provider": full_result["provider"],
            "coordinates": full_result["coordinates"],
            "timezone": full_result["timezone"],
            "daily_forecast": full_result["daily_forecast"],
            "units": full_result["units"],
        }


# Module-level convenience singleton instance
weather_service = WeatherService.get_instance()


def get_weather_for_field(
    field_id: str,
    forecast_days: int = 7,
    timezone: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function delegating to WeatherService singleton."""
    return weather_service.get_weather_for_field(field_id, forecast_days, timezone)


def get_current_weather_for_field(
    field_id: str,
    timezone: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function delegating to WeatherService singleton."""
    return weather_service.get_current_weather_for_field(field_id, timezone)


def get_forecast_for_field(
    field_id: str,
    forecast_days: int = 7,
    timezone: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience function delegating to WeatherService singleton."""
    return weather_service.get_forecast_for_field(field_id, forecast_days, timezone)

