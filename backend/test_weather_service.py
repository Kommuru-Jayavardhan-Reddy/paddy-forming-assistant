"""
Paddy Farming Assistant - Weather Service Test Suite (STEP 11E.2)
Tests coordinate validation, provider payload parsing, missing field resilience,
error handling (network, timeouts, HTTP errors, malformed JSON), service toggles,
and executes verified live Open-Meteo API queries for real field coordinates.
"""

import math
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests
from app import config
from app.exceptions import (
    InvalidCoordinatesError,
    WeatherServiceDisabledError,
    WeatherServiceUnavailableError,
    WeatherProviderError,
    WeatherParsingError,
)
from app.services.weather_service import (
    WeatherService,
    WMO_WEATHER_CODE_DESCRIPTIONS,
    _safe_float,
    _safe_int,
)

# Representative sample Open-Meteo JSON payload for unit testing
MOCK_OPEN_METEO_PAYLOAD = {
    "latitude": 13.285588,
    "longitude": 79.29686,
    "generationtime_ms": 0.045,
    "utc_offset_seconds": 19800,
    "timezone": "Asia/Kolkata",
    "timezone_abbreviation": "IST",
    "elevation": 182.0,
    "current_units": {
        "time": "iso8601",
        "interval": "seconds",
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "precipitation": "mm",
        "rain": "mm",
        "wind_speed_10m": "km/h",
        "weather_code": "wmo code",
    },
    "current": {
        "time": "2026-10-13T18:00",
        "interval": 900,
        "temperature_2m": 29.4,
        "relative_humidity_2m": 65,
        "precipitation": 0.2,
        "rain": 0.2,
        "wind_speed_10m": 12.3,
        "weather_code": 61,
    },
    "daily_units": {
        "time": "iso8601",
        "temperature_2m_max": "°C",
        "temperature_2m_min": "°C",
        "precipitation_sum": "mm",
        "rain_sum": "mm",
        "wind_speed_10m_max": "km/h",
        "weather_code": "wmo code",
    },
    "daily": {
        "time": ["2026-10-13", "2026-10-14", "2026-10-15"],
        "temperature_2m_max": [32.5, 31.8, 30.2],
        "temperature_2m_min": [23.1, 22.9, 23.4],
        "precipitation_sum": [1.5, 4.2, 0.0],
        "rain_sum": [1.2, 3.8, 0.0],
        "wind_speed_10m_max": [15.2, 18.0, 11.5],
        "weather_code": [61, 63, 1],
    },
}


def test_helper_safe_conversions():
    print("\n[Test 1] Testing Helper Converters (_safe_float, _safe_int)...")
    assert _safe_float("28.5") == 28.5
    assert _safe_float(30.1234) == 30.12
    assert _safe_float(None) is None
    assert _safe_float("invalid") is None
    assert _safe_float(float("nan")) is None
    assert _safe_float(float("inf")) is None

    assert _safe_int(61) == 61
    assert _safe_int("53") == 53
    assert _safe_int(None) is None
    assert _safe_int("invalid") is None
    print("  [PASS] Safe conversion helpers correctly handle valid, null, nan, and corrupt inputs.")


def test_coordinate_validation():
    print("\n[Test 2] Testing Coordinate Validation...")
    service = WeatherService(base_url="https://api.open-meteo.com/v1/forecast")

    # Valid field coordinates (FIELD_01 and boundaries)
    lat, lon = service.validate_coordinates(13.285588, 79.296860)
    assert lat == 13.285588 and lon == 79.296860

    lat_b, lon_b = service.validate_coordinates(-90.0, -180.0)
    assert lat_b == -90.0 and lon_b == -180.0

    lat_b2, lon_b2 = service.validate_coordinates(90.0, 180.0)
    assert lat_b2 == 90.0 and lon_b2 == 180.0

    # Invalid latitude out of range
    try:
        service.validate_coordinates(91.5, 79.0)
        assert False, "Should have raised InvalidCoordinatesError for latitude > 90"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400
        print(f"  [PASS] Caught expected invalid latitude: {e.message}")

    try:
        service.validate_coordinates(-91.0, 79.0)
        assert False, "Should have raised InvalidCoordinatesError for latitude < -90"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400

    # Invalid longitude out of range
    try:
        service.validate_coordinates(13.0, 181.0)
        assert False, "Should have raised InvalidCoordinatesError for longitude > 180"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400
        print(f"  [PASS] Caught expected invalid longitude: {e.message}")

    try:
        service.validate_coordinates(13.0, -181.0)
        assert False, "Should have raised InvalidCoordinatesError for longitude < -180"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400

    # Non-numeric or None coordinates
    try:
        service.validate_coordinates("abc", 79.0)
        assert False, "Should have raised InvalidCoordinatesError for non-numeric latitude"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400

    try:
        service.validate_coordinates(None, 79.0)
        assert False, "Should have raised InvalidCoordinatesError for None latitude"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400

    # NaN / Inf coordinates
    try:
        service.validate_coordinates(float("nan"), 79.0)
        assert False, "Should have raised InvalidCoordinatesError for NaN latitude"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400

    try:
        service.validate_coordinates(13.0, float("inf"))
        assert False, "Should have raised InvalidCoordinatesError for Inf longitude"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400

    print("  [PASS] Coordinate boundary and type validation checks passed.")


def test_mock_successful_response_parsing():
    print("\n[Test 3] Testing Parsing of Representative Open-Meteo Payload (Mocked)...")
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPEN_METEO_PAYLOAD
    mock_session.get.return_value = mock_response

    service = WeatherService(session=mock_session)
    result = service.get_weather(latitude=13.285588, longitude=79.296860)

    # Provider and coordinate verification
    assert result["provider"] == config.WEATHER_PROVIDER
    assert result["coordinates"]["latitude"] == 13.29  # _safe_float rounded
    assert result["coordinates"]["longitude"] == 79.3
    assert result["coordinates"]["elevation"] == 182.0
    assert result["timezone"] == "Asia/Kolkata"
    assert result["utc_offset_seconds"] == 19800

    # Current weather verification
    current = result["current"]
    assert current is not None
    assert current["time"] == "2026-10-13T18:00"
    assert current["temperature"] == 29.4
    assert current["temperature_unit"] == "°C"
    assert current["relative_humidity"] == 65.0
    assert current["precipitation"] == 0.2
    assert current["rain"] == 0.2
    assert current["wind_speed"] == 12.3
    assert current["weather_code"] == 61
    assert current["weather_condition"] == "Slight rain"  # Mapped via WMO table

    # Daily forecast verification
    daily = result["daily_forecast"]
    assert len(daily) == 3
    day1 = daily[0]
    assert day1["date"] == "2026-10-13"
    assert day1["temperature_max"] == 32.5
    assert day1["temperature_min"] == 23.1
    assert day1["precipitation_sum"] == 1.5
    assert day1["rain_sum"] == 1.2
    assert day1["wind_speed_max"] == 15.2
    assert day1["weather_code"] == 61
    assert day1["weather_condition"] == "Slight rain"

    day3 = daily[2]
    assert day3["weather_code"] == 1
    assert day3["weather_condition"] == "Mainly clear"

    # Units verification
    assert result["units"]["temperature"] == "°C"
    assert result["units"]["relative_humidity"] == "%"
    assert result["units"]["precipitation"] == "mm"
    assert result["units"]["wind_speed"] == "km/h"

    print("  [PASS] Representative payload parsed cleanly into unified domain structure.")


def test_mock_missing_optional_fields():
    print("\n[Test 4] Testing Missing and Null Optional Fields (No Fabrication)...")
    sparse_payload = {
        "latitude": 13.28,
        "longitude": 79.29,
        "timezone": "Asia/Kolkata",
        "current": {
            "time": "2026-10-13T18:00",
            "temperature_2m": 30.0,
            # relative_humidity_2m is missing
            # precipitation is missing
            # rain is missing
            # wind_speed_10m is null
            "wind_speed_10m": None,
            # weather_code is missing
        },
        # daily is missing entirely
    }

    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = sparse_payload
    mock_session.get.return_value = mock_resp

    service = WeatherService(session=mock_session)
    result = service.get_weather(latitude=13.28, longitude=79.29)

    current = result["current"]
    assert current["temperature"] == 30.0
    assert current["relative_humidity"] is None
    assert current["precipitation"] is None
    assert current["rain"] is None
    assert current["wind_speed"] is None
    assert current["weather_code"] is None
    assert current["weather_condition"] is None

    # Daily forecast should be an empty list, not fabricated
    assert result["daily_forecast"] == []

    print("  [PASS] Missing and null fields safely remain None; zero synthetic data fabricated.")


def test_mock_timeout_error_handling():
    print("\n[Test 5] Testing Network Timeout Handling (Mocked)...")
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.Timeout("Connection timed out after 10.0s")

    service = WeatherService(session=mock_session)
    try:
        service.get_weather(13.28, 79.29)
        assert False, "Should have raised WeatherServiceUnavailableError on timeout"
    except WeatherServiceUnavailableError as e:
        assert e.status_code == 503
        assert "timed out" in e.message.lower()
        print(f"  [PASS] Handled timeout gracefully with 503: {e.message}")


def test_mock_connection_error_handling():
    print("\n[Test 6] Testing Network Connection Error Handling (Mocked)...")
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.ConnectionError("Failed to establish a new connection")

    service = WeatherService(session=mock_session)
    try:
        service.get_weather(13.28, 79.29)
        assert False, "Should have raised WeatherServiceUnavailableError on connection error"
    except WeatherServiceUnavailableError as e:
        assert e.status_code == 503
        assert "unable to connect" in e.message.lower()
        print(f"  [PASS] Handled connection failure gracefully with 503: {e.message}")


def test_mock_http_error_handling():
    print("\n[Test 7] Testing HTTP Error Handling (Mocked)...")
    # HTTP 400 Bad Request
    mock_session = MagicMock()
    mock_400 = MagicMock()
    mock_400.status_code = 400
    mock_400.text = '{"error": true, "reason": "Invalid parameter"}'
    mock_session.get.return_value = mock_400

    service = WeatherService(session=mock_session)
    try:
        service.get_weather(13.28, 79.29)
        assert False, "Should have raised WeatherProviderError for HTTP 400"
    except WeatherProviderError as e:
        assert e.status_code == 502
        assert "400" in e.message
        print(f"  [PASS] Handled HTTP 400 with 502 Bad Gateway: {e.message}")

    # HTTP 503 Service Unavailable
    mock_503 = MagicMock()
    mock_503.status_code = 503
    mock_session.get.return_value = mock_503
    try:
        service.get_weather(13.28, 79.29)
        assert False, "Should have raised WeatherServiceUnavailableError for HTTP 503"
    except WeatherServiceUnavailableError as e:
        assert e.status_code == 503
        assert "503" in e.message
        print(f"  [PASS] Handled HTTP 503 with 503 Service Unavailable: {e.message}")


def test_mock_malformed_json_handling():
    print("\n[Test 8] Testing Malformed JSON and Unexpected Structures (Mocked)...")
    mock_session = MagicMock()
    mock_invalid_json = MagicMock()
    mock_invalid_json.status_code = 200
    mock_invalid_json.json.side_effect = requests.exceptions.JSONDecodeError("Expecting value", "doc", 0)
    mock_session.get.return_value = mock_invalid_json

    service = WeatherService(session=mock_session)
    try:
        service.get_weather(13.28, 79.29)
        assert False, "Should have raised WeatherParsingError for malformed JSON"
    except WeatherParsingError as e:
        assert e.status_code == 502
        print(f"  [PASS] Handled malformed JSON with 502: {e.message}")

    # Non-dictionary payload
    mock_list_json = MagicMock()
    mock_list_json.status_code = 200
    mock_list_json.json.return_value = ["not", "a", "dict"]
    mock_session.get.return_value = mock_list_json
    try:
        service.get_weather(13.28, 79.29)
        assert False, "Should have raised WeatherParsingError for non-dict payload"
    except WeatherParsingError as e:
        assert e.status_code == 502
        print(f"  [PASS] Handled non-dict JSON structure with 502: {e.message}")


def test_service_disabled_flag():
    print("\n[Test 9] Testing Weather Service Enabled/Disabled Flag...")
    service = WeatherService()
    with patch("app.config.WEATHER_SERVICE_ENABLED", False):
        try:
            service.get_weather(13.28, 79.29)
            assert False, "Should have raised WeatherServiceDisabledError when disabled"
        except WeatherServiceDisabledError as e:
            assert e.status_code == 503
            print(f"  [PASS] Handled disabled service with 503: {e.message}")


def test_specialized_accessors():
    print("\n[Test 10] Testing Specialized Accessors (get_current_weather, get_forecast)...")
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPEN_METEO_PAYLOAD
    mock_session.get.return_value = mock_response

    service = WeatherService(session=mock_session)

    # get_current_weather
    curr_res = service.get_current_weather(13.285588, 79.296860)
    assert "current" in curr_res
    assert "daily_forecast" not in curr_res
    assert curr_res["current"]["temperature"] == 29.4
    print("  [PASS] get_current_weather returns strictly current snapshot.")

    # get_forecast
    fc_res = service.get_forecast(13.285588, 79.296860, forecast_days=3)
    assert "daily_forecast" in fc_res
    assert "current" not in fc_res
    assert len(fc_res["daily_forecast"]) == 3
    print("  [PASS] get_forecast returns strictly forecast series.")


def test_live_open_meteo_api():
    print("\n[Test 11] Executing REAL LIVE Open-Meteo Integration Query...")
    print("  (Querying actual Open-Meteo endpoint: https://api.open-meteo.com/v1/forecast)")
    
    # Real field coordinates from field_locations.csv (FIELD_01: Chittoor district, Andhra Pradesh)
    real_lat = 13.285588
    real_lon = 79.296860

    service = WeatherService()
    try:
        live_result = service.get_weather(
            latitude=real_lat,
            longitude=real_lon,
            timezone="Asia/Kolkata",
            forecast_days=7,
        )

        assert live_result["provider"] == "Open-Meteo"
        assert live_result["timezone"] == "Asia/Kolkata"
        assert abs(live_result["coordinates"]["latitude"] - real_lat) < 0.1
        assert abs(live_result["coordinates"]["longitude"] - real_lon) < 0.1

        current = live_result["current"]
        assert current is not None
        assert current["temperature"] is not None
        assert current["relative_humidity"] is not None
        assert current["wind_speed"] is not None
        assert current["temperature_unit"] == "°C"

        print(f"  [LIVE OK] Retrieved Current Weather:")
        print(f"    - Observation Time:  {current.get('time')}")
        print(f"    - Temperature:       {current.get('temperature')} {current.get('temperature_unit')}")
        print(f"    - Relative Humidity: {current.get('relative_humidity')} {current.get('relative_humidity_unit')}")
        print(f"    - Precipitation:     {current.get('precipitation')} {current.get('precipitation_unit')}")
        print(f"    - Rain:              {current.get('rain')} {current.get('rain_unit')}")
        print(f"    - Wind Speed:        {current.get('wind_speed')} {current.get('wind_speed_unit')}")
        print(f"    - Weather Code:      {current.get('weather_code')} ({current.get('weather_condition')})")

        forecast = live_result["daily_forecast"]
        assert len(forecast) == 7, f"Expected 7 forecast days, got {len(forecast)}"
        print(f"  [LIVE OK] Retrieved 7-Day Forecast (first day: {forecast[0]['date']}, max: {forecast[0]['temperature_max']}°C, min: {forecast[0]['temperature_min']}°C, condition: {forecast[0]['weather_condition']})")
        print("  [PASS] Real Open-Meteo API query completed and verified successfully.")
    except Exception as e:
        print(f"  [WARN] Live network call to Open-Meteo encountered an issue: {e}")
        raise e


def run_all_tests():
    print("=" * 70)
    print("STEP 11E.2 — WEATHER SERVICE COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    test_helper_safe_conversions()
    test_coordinate_validation()
    test_mock_successful_response_parsing()
    test_mock_missing_optional_fields()
    test_mock_timeout_error_handling()
    test_mock_connection_error_handling()
    test_mock_http_error_handling()
    test_mock_malformed_json_handling()
    test_service_disabled_flag()
    test_specialized_accessors()
    test_live_open_meteo_api()

    print("\n" + "=" * 70)
    print("ALL STEP 11E.2 WEATHER SERVICE TESTS PASSED SUCCESSFULLY (PASS)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
