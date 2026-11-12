"""
Paddy Farming Assistant - Location-Based Weather Data Integration Test Suite (STEP 11E.3)
Tests authoritative coordinate resolution for verified paddy fields,
connection to WeatherService, error propagation for unknown fields and invalid coordinates,
service disablement, provider errors, and real live Open-Meteo field queries.
"""

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import config
from app.exceptions import (
    FieldNotFoundError,
    InvalidCoordinatesError,
    WeatherServiceDisabledError,
    WeatherServiceUnavailableError,
    WeatherProviderError,
    WeatherParsingError,
)
from app.services.field_mapping import FieldMappingService
from app.services.weather_service import (
    WeatherService,
    get_weather_for_field,
    get_current_weather_for_field,
    get_forecast_for_field,
)

# Standard mock Open-Meteo response
MOCK_WEATHER_PAYLOAD = {
    "latitude": 13.285588,
    "longitude": 79.29686,
    "generationtime_ms": 0.05,
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
        "precipitation": 0.0,
        "rain": 0.0,
        "wind_speed_10m": 12.3,
        "weather_code": 0,
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
        "weather_code": [0, 61, 2],
    },
}


def test_field_01_coordinate_resolution():
    print("\n[Test 1] Verifying FIELD_01 Coordinate Resolution...")
    field_service = FieldMappingService.get_instance()
    lat, lon = field_service.get_field_coordinates("FIELD_01")

    assert isinstance(lat, float) and isinstance(lon, float)
    assert abs(lat - 13.285588) < 1e-5, f"Expected lat ~13.285588, got {lat}"
    assert abs(lon - 79.296860) < 1e-5, f"Expected lon ~79.296860, got {lon}"

    # Verify case-insensitivity ('field_01' -> same coordinates)
    lat_lower, lon_lower = field_service.get_field_coordinates("field_01")
    assert lat == lat_lower and lon == lon_lower
    print(f"  [PASS] FIELD_01 coordinates resolved accurately: lat={lat:.6f}, lon={lon:.6f}")


def test_multiple_distinct_fields_coordinates():
    print("\n[Test 2] Verifying Multiple Distinct Fields Use Their Own Coordinates...")
    field_service = FieldMappingService.get_instance()

    lat1, lon1 = field_service.get_field_coordinates("FIELD_01")
    lat2, lon2 = field_service.get_field_coordinates("FIELD_02")
    lat58, lon58 = field_service.get_field_coordinates("FIELD_58")

    # Verify FIELD_02 coordinates match field_locations.csv (13.429626, 79.581415)
    assert abs(lat2 - 13.429626) < 1e-5
    assert abs(lon2 - 79.581415) < 1e-5

    # Verify FIELD_58 coordinates match field_locations.csv (13.32715, 79.55277)
    assert abs(lat58 - 13.32715) < 1e-5
    assert abs(lon58 - 79.55277) < 1e-5

    # Verify no silent substitution of FIELD_01 for other fields
    assert (lat1, lon1) != (lat2, lon2), "FIELD_02 must not duplicate FIELD_01 coordinates"
    assert (lat1, lon1) != (lat58, lon58), "FIELD_58 must not duplicate FIELD_01 coordinates"
    assert (lat2, lon2) != (lat58, lon58), "FIELD_58 must not duplicate FIELD_02 coordinates"
    print(f"  [PASS] Distinct field locations verified (FIELD_01: {lat1:.4f},{lon1:.4f} | FIELD_02: {lat2:.4f},{lon2:.4f} | FIELD_58: {lat58:.4f},{lon58:.4f})")


def test_weather_service_receives_resolved_coordinates():
    print("\n[Test 3] Verifying WeatherService Receives Resolved Coordinates (Mocked)...")
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_WEATHER_PAYLOAD
    mock_session.get.return_value = mock_resp

    weather_svc = WeatherService(session=mock_session)
    result = weather_svc.get_weather_for_field("FIELD_01", forecast_days=3)

    # Check session.get was called with exact resolved coordinates
    mock_session.get.assert_called_once()
    call_args, call_kwargs = mock_session.get.call_args
    passed_params = call_kwargs["params"]

    assert abs(passed_params["latitude"] - 13.285588) < 1e-5
    assert abs(passed_params["longitude"] - 79.296860) < 1e-5
    assert passed_params["forecast_days"] == 3
    assert passed_params["timezone"] == "Asia/Kolkata"

    # Verify return structure preserves requested & canonical identifiers
    assert result["field_id"] == "FIELD_01"
    assert result["requested_field_id"] == "FIELD_01"
    assert result["clean_field_id"] == "CLEAN_FIELD_001"
    assert result["coordinates"]["latitude"] == 13.285588
    assert result["coordinates"]["longitude"] == 79.296860
    assert result["current"]["temperature"] == 29.4
    assert len(result["daily_forecast"]) == 3
    print("  [PASS] WeatherService received exact resolved field coordinates and preserved metadata.")


def test_second_known_field_dispatch():
    print("\n[Test 4] Verifying Second Known Field (FIELD_02) Dispatches Its Own Coordinates...")
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_WEATHER_PAYLOAD
    mock_session.get.return_value = mock_resp

    weather_svc = WeatherService(session=mock_session)
    result = weather_svc.get_weather_for_field("FIELD_02", forecast_days=7)

    passed_params = mock_session.get.call_args[1]["params"]
    assert abs(passed_params["latitude"] - 13.429626) < 1e-5
    assert abs(passed_params["longitude"] - 79.581415) < 1e-5
    assert result["field_id"] == "FIELD_02"
    assert result["clean_field_id"] == "CLEAN_FIELD_002"
    print("  [PASS] FIELD_02 queried Open-Meteo with Lat: 13.429626, Lon: 79.581415.")


def test_unknown_field_rejection():
    print("\n[Test 5] Verifying Unknown Field ID Rejection (404)...")
    field_service = FieldMappingService.get_instance()
    weather_svc = WeatherService()

    # In FieldMappingService directly
    try:
        field_service.get_field_coordinates("FIELD_99")
        assert False, "Should have raised FieldNotFoundError for FIELD_99"
    except FieldNotFoundError as e:
        assert e.status_code == 404
        print(f"  [PASS] FieldMappingService correctly raised 404: {e.message}")

    try:
        field_service.get_field_coordinates("UNKNOWN_FIELD_XYZ")
        assert False, "Should have raised FieldNotFoundError for UNKNOWN_FIELD_XYZ"
    except FieldNotFoundError as e:
        assert e.status_code == 404

    # In WeatherService
    try:
        weather_svc.get_weather_for_field("FIELD_99")
        assert False, "Should have raised FieldNotFoundError for FIELD_99"
    except FieldNotFoundError as e:
        assert e.status_code == 404
        print(f"  [PASS] WeatherService.get_weather_for_field correctly raised 404: {e.message}")


def test_missing_and_invalid_coordinates_handling():
    print("\n[Test 6] Verifying Missing and Invalid Coordinates Handling (400)...")
    field_service = FieldMappingService.get_instance()

    # None / empty field_id
    try:
        field_service.get_field_coordinates("")
        assert False, "Should have raised FieldNotFoundError for empty string"
    except FieldNotFoundError as e:
        assert e.status_code == 404

    try:
        field_service.get_field_coordinates(None)
        assert False, "Should have raised FieldNotFoundError for None"
    except FieldNotFoundError as e:
        assert e.status_code == 404

    # Inject mock corrupted field into master catalog to test safety guards
    field_service._master_fields["TEST_CORRUPT_COORDS"] = {
        "field_id": "TEST_CORRUPT_COORDS",
        "latitude": 999.0,  # Out of range
        "longitude": 79.0,
    }
    try:
        field_service.get_field_coordinates("TEST_CORRUPT_COORDS")
        assert False, "Should have raised InvalidCoordinatesError for lat=999.0"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400
        print(f"  [PASS] Handled out-of-range coordinates with 400: {e.message}")

    field_service._master_fields["TEST_NAN_COORDS"] = {
        "field_id": "TEST_NAN_COORDS",
        "latitude": float("nan"),
        "longitude": 79.0,
    }
    try:
        field_service.get_field_coordinates("TEST_NAN_COORDS")
        assert False, "Should have raised InvalidCoordinatesError for lat=nan"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400
        print(f"  [PASS] Handled NaN coordinates with 400: {e.message}")

    field_service._master_fields["TEST_NONE_COORDS"] = {
        "field_id": "TEST_NONE_COORDS",
        "latitude": None,
        "longitude": 79.0,
    }
    try:
        field_service.get_field_coordinates("TEST_NONE_COORDS")
        assert False, "Should have raised InvalidCoordinatesError for lat=None"
    except InvalidCoordinatesError as e:
        assert e.status_code == 400
        print(f"  [PASS] Handled missing coordinates with 400: {e.message}")

    # Clean up mock fields
    del field_service._master_fields["TEST_CORRUPT_COORDS"]
    del field_service._master_fields["TEST_NAN_COORDS"]
    del field_service._master_fields["TEST_NONE_COORDS"]


def test_weather_service_error_propagation():
    print("\n[Test 7] Verifying Weather Service Errors Propagate from Field Method...")
    # 1. Weather service disabled
    weather_svc = WeatherService()
    with patch("app.config.WEATHER_SERVICE_ENABLED", False):
        try:
            weather_svc.get_weather_for_field("FIELD_01")
            assert False, "Should have raised WeatherServiceDisabledError"
        except WeatherServiceDisabledError as e:
            assert e.status_code == 503
            print(f"  [PASS] Propagated WeatherServiceDisabledError (503): {e.message}")

    # 2. Timeout error propagation
    mock_session = MagicMock()
    mock_session.get.side_effect = WeatherServiceUnavailableError("Weather request timed out.")
    mock_weather_svc = WeatherService(session=mock_session)
    try:
        mock_weather_svc.get_weather_for_field("FIELD_01")
        assert False, "Should have raised WeatherServiceUnavailableError on timeout"
    except WeatherServiceUnavailableError as e:
        assert e.status_code == 503
        print(f"  [PASS] Propagated WeatherServiceUnavailableError (503): {e.message}")

    # 3. Provider 400 error propagation
    mock_session2 = MagicMock()
    mock_resp400 = MagicMock()
    mock_resp400.status_code = 400
    mock_resp400.text = "Invalid request"
    mock_session2.get.return_value = mock_resp400
    mock_weather_svc2 = WeatherService(session=mock_session2)
    try:
        mock_weather_svc2.get_weather_for_field("FIELD_01")
        assert False, "Should have raised WeatherProviderError on 400"
    except WeatherProviderError as e:
        assert e.status_code == 502
        print(f"  [PASS] Propagated WeatherProviderError (502): {e.message}")


def test_specialized_field_accessors():
    print("\n[Test 8] Verifying Specialized Field Accessors (current, forecast, module functions)...")
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_WEATHER_PAYLOAD
    mock_session.get.return_value = mock_resp

    weather_svc = WeatherService(session=mock_session)

    # get_current_weather_for_field
    current_res = weather_svc.get_current_weather_for_field("FIELD_01")
    assert current_res["field_id"] == "FIELD_01"
    assert "current" in current_res
    assert "daily_forecast" not in current_res
    assert current_res["current"]["temperature"] == 29.4
    print("  [PASS] get_current_weather_for_field returns strictly current field snapshot.")

    # get_forecast_for_field
    forecast_res = weather_svc.get_forecast_for_field("FIELD_01", forecast_days=3)
    assert forecast_res["field_id"] == "FIELD_01"
    assert "daily_forecast" in forecast_res
    assert "current" not in forecast_res
    assert len(forecast_res["daily_forecast"]) == 3
    print("  [PASS] get_forecast_for_field returns strictly daily forecast series.")


def test_live_open_meteo_for_field():
    print("\n[Test 9] Executing REAL LIVE Open-Meteo Query for FIELD_01...")
    print("  (Resolving FIELD_01 -> (13.285588, 79.296860) and calling Open-Meteo live)")

    try:
        live_res = get_weather_for_field("FIELD_01", forecast_days=7)
        assert live_res["field_id"] == "FIELD_01"
        assert live_res["clean_field_id"] == "CLEAN_FIELD_001"
        assert live_res["provider"] == "Open-Meteo"
        assert live_res["timezone"] == "Asia/Kolkata"
        assert abs(live_res["coordinates"]["latitude"] - 13.285588) < 1e-4
        assert abs(live_res["coordinates"]["longitude"] - 79.296860) < 1e-4

        current = live_res["current"]
        assert current is not None
        assert current["temperature"] is not None
        assert current["relative_humidity"] is not None
        assert current["wind_speed"] is not None

        forecast = live_res["daily_forecast"]
        assert len(forecast) == 7

        print(f"  [LIVE OK] Field: {live_res['field_id']} ({live_res['clean_field_id']})")
        print(f"  [LIVE OK] Coords: Lat {live_res['coordinates']['latitude']}, Lon {live_res['coordinates']['longitude']}")
        print(f"  [LIVE OK] Current: {current['temperature']}°C, {current['relative_humidity']}%, Wind: {current['wind_speed']} km/h, Code: {current['weather_code']} ({current['weather_condition']})")
        print(f"  [LIVE OK] 7-Day Forecast: retrieved {len(forecast)} days (Day 1: {forecast[0]['date']}, max {forecast[0]['temperature_max']}°C, min {forecast[0]['temperature_min']}°C)")
        print("  [PASS] Live field-to-weather integration verified successfully.")
    except Exception as e:
        print(f"  [WARN] Live network call encountered an error: {e}")
        raise e


def run_all_tests():
    print("=" * 70)
    print("STEP 11E.3 — LOCATION-BASED WEATHER DATA INTEGRATION TEST SUITE")
    print("=" * 70)

    test_field_01_coordinate_resolution()
    test_multiple_distinct_fields_coordinates()
    test_weather_service_receives_resolved_coordinates()
    test_second_known_field_dispatch()
    test_unknown_field_rejection()
    test_missing_and_invalid_coordinates_handling()
    test_weather_service_error_propagation()
    test_specialized_field_accessors()
    test_live_open_meteo_for_field()

    print("\n" + "=" * 70)
    print("ALL STEP 11E.3 LOCATION WEATHER INTEGRATION TESTS PASSED (PASS)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
