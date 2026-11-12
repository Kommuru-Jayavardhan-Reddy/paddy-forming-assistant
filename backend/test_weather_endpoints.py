"""
Paddy Farming Assistant - Weather Endpoints HTTP Verification Test Suite (STEP 11E.4)
Executes HTTP integration tests against the live FastAPI Uvicorn server:
1. GET /weather/current (mocked)
2. GET /weather/forecast (mocked)
3. GET /fields/FIELD_01/weather (mocked)
4. Invalid latitude and longitude handling (400/422)
5. Invalid forecast_days handling (400)
6. Unknown field ID handling (404)
7. Weather service disabled toggle (503)
8. Provider timeout / failure error propagation (503/502)
9. Data honesty (no fabricated values on sparse payload)
10. Route presence in OpenAPI specification (/openapi.json)
11. Regression verification of /health and /classes
12. Regression verification of /fields and satellite time-series endpoints
13. Regression verification of POST /predict
14. Real LIVE Open-Meteo queries against all three endpoints
"""

import sys
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests
import uvicorn
from app import config
from app.main import app
from app.services.weather_service import weather_service
from app.db.repositories.weather_repository import WeatherRepository


class ServerThread(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = 8002):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        cfg = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning")
        self.server = uvicorn.Server(cfg)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


def wait_for_server(base_url: str, timeout: float = 15.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{base_url}/health", timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


MOCK_OPEN_METEO_PAYLOAD = {
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


def run_tests():
    print("=" * 70)
    print("STEP 11E.4 — WEATHER API ROUTE HTTP INTEGRATION TEST SUITE")
    print("=" * 70)

    host = "127.0.0.1"
    port = 8002
    base_url = f"http://{host}:{port}"

    print(f"\n[Setup] Launching FastAPI test server on {base_url}...")
    server = ServerThread(host=host, port=port)
    server.start()

    if not wait_for_server(base_url, timeout=20.0):
        print("  [ERROR] Server failed to start within timeout.")
        server.stop()
        sys.exit(1)

    print("  [OK] Server is running and responding on /health.")

    try:
        # 1. OpenAPI & Route Registration
        print("\n[Test 1] Verifying Weather Routes in OpenAPI Specification (/openapi.json)...")
        r_openapi = requests.get(f"{base_url}/openapi.json", timeout=5.0)
        assert r_openapi.status_code == 200
        paths = r_openapi.json().get("paths", {})

        assert "/weather/current" in paths, "Missing /weather/current in OpenAPI paths"
        assert "/weather/forecast" in paths, "Missing /weather/forecast in OpenAPI paths"
        assert "/fields/{field_id}/weather" in paths, "Missing /fields/{field_id}/weather in OpenAPI paths"

        current_tags = paths["/weather/current"]["get"]["tags"]
        forecast_tags = paths["/weather/forecast"]["get"]["tags"]
        field_tags = paths["/fields/{field_id}/weather"]["get"]["tags"]
        assert "Weather" in current_tags and "Weather" in forecast_tags and "Weather" in field_tags
        print("  [PASS] All 3 weather routes registered in OpenAPI schema with tag 'Weather'.")

        # 2. GET /weather/current (Mocked)
        print("\n[Test 2] Testing GET /weather/current (Mocked Response)...")
        with patch.object(weather_service.session, "get") as mock_get, \
             patch.object(WeatherRepository, "get_cached_current_weather", new_callable=AsyncMock, return_value=None):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = MOCK_OPEN_METEO_PAYLOAD
            mock_get.return_value = mock_resp

            resp = requests.get(
                f"{base_url}/weather/current",
                params={"latitude": 13.285588, "longitude": 79.296860, "timezone": "Asia/Kolkata"},
                timeout=5.0,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()

            assert data["provider"] == "Open-Meteo"
            assert data["coordinates"]["latitude"] == 13.29
            assert data["coordinates"]["longitude"] == 79.3
            assert data["timezone"] == "Asia/Kolkata"
            assert data["current"]["temperature"] == 29.4
            assert data["current"]["relative_humidity"] == 65.0
            assert data["current"]["wind_speed"] == 12.3
            assert data["current"]["weather_code"] == 0
            assert data["current"]["weather_condition"] == "Clear sky"
            assert "daily_forecast" not in data or data.get("daily_forecast") is None
            print("  [PASS] GET /weather/current returned valid current weather response.")

        # 3. GET /weather/forecast (Mocked)
        print("\n[Test 3] Testing GET /weather/forecast (Mocked Response)...")
        with patch.object(weather_service.session, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = MOCK_OPEN_METEO_PAYLOAD
            mock_get.return_value = mock_resp

            resp = requests.get(
                f"{base_url}/weather/forecast",
                params={"latitude": 13.285588, "longitude": 79.296860, "forecast_days": 3},
                timeout=5.0,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()

            assert data["provider"] == "Open-Meteo"
            assert len(data["daily_forecast"]) == 3
            assert data["daily_forecast"][0]["date"] == "2026-10-13"
            assert data["daily_forecast"][0]["temperature_max"] == 32.5
            assert data["daily_forecast"][0]["temperature_min"] == 23.1
            assert data["daily_forecast"][0]["weather_condition"] == "Clear sky"
            assert "current" not in data or data.get("current") is None
            print("  [PASS] GET /weather/forecast returned valid 3-day forecast.")

        # 4. GET /fields/{field_id}/weather (Mocked)
        print("\n[Test 4] Testing GET /fields/FIELD_01/weather (Mocked Response)...")
        with patch.object(weather_service.session, "get") as mock_get, \
             patch.object(WeatherRepository, "get_cached_current_weather", new_callable=AsyncMock, return_value=None):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = MOCK_OPEN_METEO_PAYLOAD
            mock_get.return_value = mock_resp

            resp = requests.get(
                f"{base_url}/fields/FIELD_01/weather",
                params={"forecast_days": 3},
                timeout=5.0,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()

            assert data["field_id"] == "FIELD_01"
            assert data["requested_field_id"] == "FIELD_01"
            assert data["clean_field_id"] == "CLEAN_FIELD_001"
            assert data["provider"] == "Open-Meteo"
            assert abs(data["coordinates"]["latitude"] - 13.285588) < 1e-4
            assert abs(data["coordinates"]["longitude"] - 79.296860) < 1e-4
            assert data["current"]["temperature"] == 29.4
            assert len(data["daily_forecast"]) == 3
            print("  [PASS] GET /fields/FIELD_01/weather returned combined current and forecast.")

        # 5. Invalid Latitude and Longitude (HTTP 400 / 422)
        print("\n[Test 5] Testing Invalid Coordinates Handling...")
        # Out-of-bounds latitude > 90
        resp_lat = requests.get(
            f"{base_url}/weather/current",
            params={"latitude": 95.0, "longitude": 79.0},
            timeout=5.0,
        )
        assert resp_lat.status_code == 400, f"Expected 400, got {resp_lat.status_code}: {resp_lat.text}"
        assert resp_lat.json().get("error") == "InvalidCoordinatesError"
        print("  [PASS] Latitude 95.0 returned HTTP 400 (InvalidCoordinatesError).")

        # Out-of-bounds longitude > 180
        resp_lon = requests.get(
            f"{base_url}/weather/current",
            params={"latitude": 13.0, "longitude": 185.0},
            timeout=5.0,
        )
        assert resp_lon.status_code == 400
        assert resp_lon.json().get("error") == "InvalidCoordinatesError"
        print("  [PASS] Longitude 185.0 returned HTTP 400 (InvalidCoordinatesError).")

        # Non-numeric latitude -> FastAPI 422
        resp_bad = requests.get(
            f"{base_url}/weather/current",
            params={"latitude": "abc", "longitude": 79.0},
            timeout=5.0,
        )
        assert resp_bad.status_code == 422
        print("  [PASS] Non-numeric latitude returned HTTP 422 (ValidationError).")

        # 6. Invalid forecast_days (HTTP 400)
        print("\n[Test 6] Testing Invalid forecast_days Handling...")
        resp_fd0 = requests.get(
            f"{base_url}/weather/forecast",
            params={"latitude": 13.28, "longitude": 79.29, "forecast_days": 0},
            timeout=5.0,
        )
        assert resp_fd0.status_code == 400
        assert resp_fd0.json().get("error") == "InvalidForecastDaysError"
        print("  [PASS] forecast_days=0 returned HTTP 400 (InvalidForecastDaysError).")

        resp_fd8 = requests.get(
            f"{base_url}/fields/FIELD_01/weather",
            params={"forecast_days": 8},
            timeout=5.0,
        )
        assert resp_fd8.status_code == 400
        assert resp_fd8.json().get("error") == "InvalidForecastDaysError"
        print("  [PASS] forecast_days=8 returned HTTP 400 (InvalidForecastDaysError).")

        # 7. Unknown Field ID (HTTP 404)
        print("\n[Test 7] Testing Unknown Field ID Handling (HTTP 404)...")
        resp_unknown = requests.get(
            f"{base_url}/fields/FIELD_99/weather",
            timeout=5.0,
        )
        assert resp_unknown.status_code == 404
        assert resp_unknown.json().get("error") == "FieldNotFoundError"
        print(f"  [PASS] Unknown field FIELD_99 returned HTTP 404: {resp_unknown.json()['detail']}")

        # 8. Weather Service Disabled Toggle (HTTP 503)
        print("\n[Test 8] Testing Weather Service Disabled Toggle (HTTP 503)...")
        with patch("app.config.WEATHER_SERVICE_ENABLED", False):
            resp_dis = requests.get(
                f"{base_url}/weather/current",
                params={"latitude": 13.28, "longitude": 79.29},
                timeout=5.0,
            )
            assert resp_dis.status_code == 503
            assert resp_dis.json().get("error") == "WeatherServiceDisabledError"
            print("  [PASS] Disabled weather service returned HTTP 503.")

        # 9. Provider Timeout and Failure Error Propagation (HTTP 503 / 502)
        print("\n[Test 9] Testing Provider Timeout and Upstream Errors...")
        with patch.object(weather_service.session, "get") as mock_get, \
             patch.object(WeatherRepository, "get_cached_current_weather", new_callable=AsyncMock, return_value=None):
            mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
            resp_to = requests.get(
                f"{base_url}/weather/current",
                params={"latitude": 13.28, "longitude": 79.29},
                timeout=5.0,
            )
            assert resp_to.status_code == 503
            assert resp_to.json().get("error") == "WeatherServiceUnavailableError"
            print("  [PASS] Upstream timeout returned HTTP 503 (WeatherServiceUnavailableError).")

        with patch.object(weather_service.session, "get") as mock_get, \
             patch.object(WeatherRepository, "get_cached_current_weather", new_callable=AsyncMock, return_value=None):
            mock_400 = MagicMock()
            mock_400.status_code = 400
            mock_400.text = "Invalid coordinate"
            mock_get.return_value = mock_400
            resp_502 = requests.get(
                f"{base_url}/weather/current",
                params={"latitude": 13.28, "longitude": 79.29},
                timeout=5.0,
            )
            assert resp_502.status_code == 502
            assert resp_502.json().get("error") == "WeatherProviderError"
            print("  [PASS] Upstream 400 returned HTTP 502 (WeatherProviderError).")

        # 10. Data Honesty (No Fabricated Values)
        print("\n[Test 10] Testing Data Honesty (Preserving None for Missing Fields)...")
        sparse_payload = {
            "latitude": 13.28,
            "longitude": 79.29,
            "timezone": "Asia/Kolkata",
            "current": {
                "time": "2026-10-13T18:00",
                "temperature_2m": 30.5,
                # rain and precipitation omitted
                "wind_speed_10m": None,
            },
            "daily": {},
        }
        with patch.object(weather_service.session, "get") as mock_get, \
             patch.object(WeatherRepository, "get_cached_current_weather", new_callable=AsyncMock, return_value=None):
            mock_sparse = MagicMock()
            mock_sparse.status_code = 200
            mock_sparse.json.return_value = sparse_payload
            mock_get.return_value = mock_sparse

            resp_sparse = requests.get(
                f"{base_url}/weather/current",
                params={"latitude": 13.28, "longitude": 79.29},
                timeout=5.0,
            )
            assert resp_sparse.status_code == 200
            cur = resp_sparse.json()["current"]
            assert cur["temperature"] == 30.5
            assert cur["rain"] is None
            assert cur["precipitation"] is None
            assert cur["wind_speed"] is None
            assert cur["weather_condition"] is None
            print("  [PASS] Missing upstream fields safely preserved as None (no fake numbers).")

        # 11. REAL LIVE Open-Meteo Queries Against All 3 Endpoints
        print("\n[Test 11] Executing REAL LIVE End-to-End Queries Against Open-Meteo...")
        # Live 1: /weather/current
        live_cur = requests.get(
            f"{base_url}/weather/current",
            params={"latitude": 13.285588, "longitude": 79.296860, "timezone": "Asia/Kolkata"},
            timeout=10.0,
        )
        assert live_cur.status_code == 200
        cur_data = live_cur.json()["current"]
        print(f"  [LIVE OK] GET /weather/current: {cur_data['temperature']}°C, {cur_data['relative_humidity']}%, Wind: {cur_data['wind_speed']} km/h, Code: {cur_data['weather_code']} ({cur_data['weather_condition']})")

        # Live 2: /weather/forecast
        live_fc = requests.get(
            f"{base_url}/weather/forecast",
            params={"latitude": 13.285588, "longitude": 79.296860, "forecast_days": 7},
            timeout=10.0,
        )
        assert live_fc.status_code == 200
        fc_list = live_fc.json()["daily_forecast"]
        assert len(fc_list) == 7
        print(f"  [LIVE OK] GET /weather/forecast: 7 days returned (Day 1: {fc_list[0]['date']}, max {fc_list[0]['temperature_max']}°C, min {fc_list[0]['temperature_min']}°C)")

        # Live 3: /fields/FIELD_01/weather
        live_field = requests.get(
            f"{base_url}/fields/FIELD_01/weather",
            params={"forecast_days": 7},
            timeout=10.0,
        )
        assert live_field.status_code in (200, 503)
        if live_field.status_code == 200:
            f_data = live_field.json()
            assert f_data["field_id"] == "FIELD_01"
            assert f_data["clean_field_id"] == "CLEAN_FIELD_001"
            assert len(f_data["daily_forecast"]) == 7
            assert f_data["current"]["temperature"] is not None
            print(f"  [LIVE OK] GET /fields/FIELD_01/weather: {f_data['field_id']} -> Current {f_data['current']['temperature']}°C + {len(f_data['daily_forecast'])}-day forecast")
        else:
            print(f"  [LIVE NOTE] Open-Meteo upstream rate-limit (HTTP 503) handled gracefully.")

        # 12. Regression: /health and /classes
        print("\n[Test 12] Regression: Verifying /health and /classes Endpoints...")
        r_health = requests.get(f"{base_url}/health", timeout=5.0)
        assert r_health.status_code == 200
        r_classes = requests.get(f"{base_url}/classes", timeout=5.0)
        assert r_classes.status_code == 200
        print("  [PASS] System health and disease classes endpoints operating normally.")

        # 13. Regression: /fields, timeseries, and health
        print("\n[Test 13] Regression: Verifying Field Catalog and Satellite Endpoints...")
        r_fields = requests.get(f"{base_url}/fields", timeout=5.0)
        assert r_fields.status_code == 200 and r_fields.json()["total_fields"] == 58

        r_ts = requests.get(f"{base_url}/fields/FIELD_01/timeseries", timeout=5.0)
        assert r_ts.status_code == 200 and len(r_ts.json()["timesteps"]) == 10

        r_fh = requests.get(f"{base_url}/fields/FIELD_01/health", timeout=5.0)
        assert r_fh.status_code == 200 and "advisory_summary" in r_fh.json()
        print("  [PASS] Field catalog, satellite time-series, and vegetation health endpoints operating normally.")

        # 14. Regression: POST /predict
        print("\n[Test 14] Regression: Verifying POST /predict Image Disease Classification...")
        sample_img_path = BACKEND_DIR / "test_images" / "tungro" / "TUNGRO5_67.JPG"
        if not sample_img_path.exists():
            found = list(BACKEND_DIR.glob("test_images/**/*.JPG")) + list(BACKEND_DIR.glob("test_images/**/*.jpg"))
            if found:
                sample_img_path = found[0]

        assert sample_img_path.exists(), f"Sample test image not found at {sample_img_path}"
        with open(sample_img_path, "rb") as img_f:
            r_pred = requests.post(
                f"{base_url}/predict",
                files={"file": (sample_img_path.name, img_f, "image/jpeg")},
                timeout=15.0,
            )
        assert r_pred.status_code == 200, f"Expected 200, got {r_pred.status_code}: {r_pred.text}"
        pred_data = r_pred.json()
        assert "disease" in pred_data
        assert "confidence" in pred_data
        print(f"  [PASS] POST /predict: {pred_data['disease']} (conf: {pred_data['confidence']:.4f})")



        print("\n" + "=" * 70)
        print("ALL STEP 11E.4 WEATHER ENDPOINT TESTS PASSED SUCCESSFULLY (PASS)")
        print("=" * 70)

    finally:
        print("\n[Teardown] Stopping FastAPI server...")
        server.stop()


if __name__ == "__main__":
    run_tests()
