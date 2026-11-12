"""
Paddy Farming Assistant - Database CRUD and FastAPI Integration Test Suite (STEP 11F.8)
Exhaustively tests all 20 Phase H criteria across PostgreSQL and FastAPI:

 1. Database connectivity
 2. Fields list from PostgreSQL (58 fields)
 3. Retrieve FIELD_01
 4. Retrieve all observations for FIELD_01 (10 timesteps)
 5. Verify 10 observations and feature ordering [NDVI, NDRE, GNDVI] matching NPY
 6. Retrieve another valid field (FIELD_58, FIELD_15)
 7. Request unknown field 404 behavior
 8. Empty satellite observations behavior
 9. Pagination and date filters
10. Prediction persistence using controlled test data
11. Model-specific class-index validation (0-12 vs 0-10)
12. Confidence validation ([0.0, 1.0])
13. Persistence rollback on simulated database failure
14. Weather caching functionality
15. Database unavailable behavior (503 response)
16. Image-only prediction regression (POST /predict)
17. Multimodal prediction regression (POST /predict/multimodal)
18. Grad-CAM and SHAP regression
19. Weather endpoint regression
20. Field health endpoint regression
"""

import asyncio
import io
import logging
import sys
import time
import threading
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock

# Force UTF-8 encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
import requests
import uvicorn
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.db.session import AsyncSessionLocal, check_db_connectivity
from app.db.models.field import Field
from app.db.models.satellite import SatelliteObservation
from app.db.models.prediction import PredictionHistory
from app.db.models.weather import WeatherRecord
from app.db.repositories.field_repository import FieldRepository
from app.db.repositories.satellite_repository import SatelliteRepository
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.weather_repository import WeatherRepository
from app.main import app


class ServerThread(threading.Thread):
    """Background Uvicorn thread for testing FastAPI HTTP endpoints."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8003):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        cfg = uvicorn.Config(app, host=self.host, port=self.port, log_level="error")
        self.server = uvicorn.Server(cfg)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


def wait_for_server(base_url: str, timeout: float = 20.0):
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


async def run_async_tests():
    """Runs repository-level asynchronous tests."""
    print("\n" + "=" * 70)
    print("PART 1: ASYNC DATABASE REPOSITORY & CRUD TESTS")
    print("=" * 70)

    # 1. Database connectivity
    print("\n[Test 1] Testing Database Connectivity...")
    conn = await check_db_connectivity()
    assert conn["connected"] is True, f"Database connectivity failed: {conn}"
    assert conn["database"] == "paddy_farming_db"
    assert conn["user"] == "paddy_app"
    print(f"  [PASS] Connected to {conn['database']} as {conn['user']} (Latency: {conn.get('latency_ms')}ms)")

    async with AsyncSessionLocal() as session:
        # 2. Fields list from PostgreSQL
        print("\n[Test 2] Testing FieldRepository.list_fields (58 Seeded Fields)...")
        field_repo = FieldRepository(session)
        fields, total = await field_repo.list_fields(skip=0, limit=100)
        assert total == 58, f"Expected 58 fields in DB, got {total}"
        assert len(fields) == 58, f"Expected 58 fields in list, got {len(fields)}"
        print(f"  [PASS] FieldRepository returned {len(fields)} fields (total: {total})")

        # 3. Retrieve FIELD_01
        print("\n[Test 3] Testing FieldRepository.get_by_external_id('FIELD_01')...")
        f01 = await field_repo.get_by_external_id("FIELD_01")
        assert f01 is not None, "FIELD_01 not found"
        assert f01.external_field_id == "FIELD_01"
        print(f"       f01.clean_field_id: {repr(f01.clean_field_id)}")
        assert round(float(f01.latitude), 6) == 13.285588
        assert round(float(f01.longitude), 6) == 79.296860
        print(f"  [PASS] Retrieved FIELD_01 (UUID: {f01.id}, GPS: {f01.latitude}, {f01.longitude})")

        # Case-insensitive resolution
        f01_lower = await field_repo.get_by_external_id("field_01")
        assert f01_lower is not None and f01_lower.id == f01.id
        print("  [PASS] Case-insensitive lookup 'field_01' resolved correctly.")

        # 4 & 5. Retrieve all observations for FIELD_01 & verify 10 observations with NPY comparison
        print("\n[Test 4 & 5] Testing SatelliteRepository for FIELD_01 (10 Observations, Features, Ordering)...")
        sat_repo = SatelliteRepository(session)
        field_res, obs = await sat_repo.get_observations_by_external_id("FIELD_01")
        assert field_res is not None
        assert len(obs) == 10, f"Expected 10 observations for FIELD_01, got {len(obs)}"

        npy_path = config.SATELLITE_SEQUENCES_PATH
        assert npy_path.exists(), f"NPY file not found at {npy_path}"
        ref_seqs = np.load(npy_path)

        for idx, o in enumerate(obs):
            assert o.time_step == idx + 1, f"Step mismatch at {idx}: expected {idx+1}, got {o.time_step}"
            assert o.observation_date is not None
            exp = ref_seqs[0, idx]
            assert np.isclose(float(o.ndvi), exp[0], atol=1e-5), f"NDVI mismatch at step {idx+1}"
            assert np.isclose(float(o.ndre), exp[1], atol=1e-5), f"NDRE mismatch at step {idx+1}"
            assert np.isclose(float(o.gndvi), exp[2], atol=1e-5), f"GNDVI mismatch at step {idx+1}"
        print(f"  [PASS] FIELD_01: 10 observations verified against bilstm_sequences.npy[0] (max diff < 1e-5)")

        # 6. Retrieve another valid field (FIELD_58 and FIELD_15)
        print("\n[Test 6] Testing FieldRepository & SatelliteRepository for FIELD_58 & FIELD_15...")
        f58, obs58 = await sat_repo.get_observations_by_external_id("FIELD_58")
        assert f58 is not None and len(obs58) == 10
        for idx, o in enumerate(obs58):
            exp = ref_seqs[57, idx]
            assert np.isclose(float(o.ndvi), exp[0], atol=1e-5)
            assert np.isclose(float(o.ndre), exp[1], atol=1e-5)
            assert np.isclose(float(o.gndvi), exp[2], atol=1e-5)
        print("  [PASS] FIELD_58: 10 observations verified against bilstm_sequences.npy[57]")

        f15, obs15 = await sat_repo.get_observations_by_external_id("FIELD_15")
        assert f15 is not None and len(obs15) == 10
        print(f"  [PASS] FIELD_15: Successfully retrieved with {len(obs15)} observations")

        # 7. Request unknown field 404 behavior
        print("\n[Test 7] Testing Repository Behavior for Nonexistent Field...")
        f_none, obs_none = await sat_repo.get_observations_by_external_id("FIELD_99")
        assert f_none is None
        assert obs_none == []
        print("  [PASS] Unknown field 'FIELD_99' returned (None, [])")

        # 8. Empty satellite observations behavior
        print("\n[Test 8] Testing Empty Observations Behavior on UUID...")
        dummy_uuid = uuid.uuid4()
        empty_obs = await sat_repo.get_observations_by_field_uuid(dummy_uuid)
        assert empty_obs == []
        print("  [PASS] Nonexistent UUID returned empty list [] without raising errors")

        # 9. Pagination and date filters
        print("\n[Test 9] Testing Pagination and Date Filtering...")
        p1, t1 = await field_repo.list_fields(skip=0, limit=10)
        p2, t2 = await field_repo.list_fields(skip=10, limit=10)
        assert len(p1) == 10 and len(p2) == 10
        assert p1[0].external_field_id != p2[0].external_field_id
        print(f"  [PASS] Pagination: page 1 ({p1[0].external_field_id}..{p1[-1].external_field_id}) != page 2 ({p2[0].external_field_id}..{p2[-1].external_field_id})")

        # Date range filter
        first_date = obs[2].observation_date
        last_date = obs[5].observation_date
        _, filtered_obs = await sat_repo.get_observations_by_external_id("FIELD_01", start_date=first_date, end_date=last_date)
        assert len(filtered_obs) == 4, f"Expected 4 filtered observations, got {len(filtered_obs)}"
        print(f"  [PASS] Date range filter [{first_date} to {last_date}] returned exactly {len(filtered_obs)} observations")

        # 10. Prediction persistence using controlled test data
        print("\n[Test 10] Testing PredictionRepository CRUD Persistence...")
        pred_repo = PredictionRepository(session)
        created_records = []

        # Image-only record
        rec_img = await pred_repo.create_prediction(
            prediction_mode="image_only",
            model_name="EfficientNet-B4",
            model_version="test_v1",
            predicted_disease="tungro",
            predicted_class_index=12,
            confidence=0.9850,
            is_healthy=False,
            top_k_predictions=[{"disease": "tungro", "probability": 0.9850, "index": 12}],
            field_id=f01.id,
            low_confidence=False,
            image_sha256="0" * 64,
            response_language="en",
            inference_latency_ms=125.5,
            device="cpu",
        )
        await session.flush()
        created_records.append(rec_img.id)
        assert rec_img.id is not None
        print(f"  [PASS] Created image_only prediction: ID={rec_img.id}, disease={rec_img.predicted_disease}")

        # Multimodal record
        rec_mm = await pred_repo.create_prediction(
            prediction_mode="multimodal",
            model_name="TemporalCrossAttention",
            model_version="test_v1",
            predicted_disease="sheath_blight",
            predicted_class_index=8,
            confidence=0.9120,
            is_healthy=False,
            top_k_predictions=[{"disease": "sheath_blight", "probability": 0.9120, "index": 8}],
            field_id=f01.id,
            attention_weights=[0.1] * 10,
            image_sha256="1" * 64,
            response_language="en",
            device="cpu",
        )
        await session.flush()
        created_records.append(rec_mm.id)
        assert rec_mm.id is not None
        print(f"  [PASS] Created multimodal prediction: ID={rec_mm.id}, disease={rec_mm.predicted_disease}")

        # List predictions
        listed, total_preds = await pred_repo.list_predictions(limit=10)
        assert total_preds >= 2
        print(f"  [PASS] list_predictions returned total={total_preds}")

        # Clean up test prediction records
        for pid in created_records:
            await session.execute(delete(PredictionHistory).where(PredictionHistory.id == pid))
        await session.commit()
        print("  [PASS] Controlled test prediction records cleaned up; table pristine.")

        # 11. Model-specific class-index validation
        print("\n[Test 11] Testing Model-Specific Class Index Validation...")
        try:
            pred_repo.validate_prediction_inputs("image_only", 13, 0.85)
            assert False, "Failed to reject invalid image_only class index 13"
        except ValueError as err:
            print(f"  [PASS] Correctly rejected image_only index 13: {err}")

        try:
            pred_repo.validate_prediction_inputs("multimodal", 11, 0.85)
            assert False, "Failed to reject invalid multimodal class index 11"
        except ValueError as err:
            print(f"  [PASS] Correctly rejected multimodal index 11: {err}")

        # Verify valid boundary cases
        pred_repo.validate_prediction_inputs("image_only", 0, 0.5)
        pred_repo.validate_prediction_inputs("image_only", 12, 0.5)
        pred_repo.validate_prediction_inputs("multimodal", 0, 0.5)
        pred_repo.validate_prediction_inputs("multimodal", 10, 0.5)
        print("  [PASS] Boundary indices 0 and 12 (image_only) and 0 and 10 (multimodal) accepted.")

        # 12. Confidence validation
        print("\n[Test 12] Testing Confidence Range Validation [0.0, 1.0]...")
        try:
            pred_repo.validate_prediction_inputs("image_only", 5, 1.05)
            assert False, "Failed to reject confidence > 1.0"
        except ValueError as err:
            print(f"  [PASS] Correctly rejected confidence 1.05: {err}")

        try:
            pred_repo.validate_prediction_inputs("image_only", 5, -0.01)
            assert False, "Failed to reject confidence < 0.0"
        except ValueError as err:
            print(f"  [PASS] Correctly rejected confidence -0.01: {err}")

        pred_repo.validate_prediction_inputs("image_only", 5, 0.0)
        pred_repo.validate_prediction_inputs("image_only", 5, 1.0)
        print("  [PASS] Boundary confidences 0.0 and 1.0 accepted.")

        # 13. Persistence rollback on simulated database failure
        print("\n[Test 13] Testing Rollback on Simulated DB Failure...")
        async with AsyncSessionLocal() as fail_session:
            base_count_res = await fail_session.execute(select(func.count(PredictionHistory.id)))
            base_count = base_count_res.scalar() or 0

            fail_repo = PredictionRepository(fail_session)
            await fail_repo.create_prediction(
                prediction_mode="image_only",
                model_name="EfficientNet-B4",
                model_version="test_v1",
                predicted_disease="tungro",
                predicted_class_index=12,
                confidence=0.95,
                is_healthy=False,
                top_k_predictions=[],
            )
            # Simulate transaction abort by calling rollback
            await fail_session.rollback()
            # Verify no records survived beyond baseline
            count_q = select(func.count(PredictionHistory.id))
            res = await fail_session.execute(count_q)
            after_count = res.scalar() or 0
            assert after_count == base_count, f"Expected {base_count} records after rollback, got {after_count}"
            print(f"  [PASS] Transaction rollback successfully verified (count unchanged: {after_count}).")

        # 14. Weather caching functionality
        print("\n[Test 14] Testing WeatherRepository Caching...")
        weather_repo = WeatherRepository(session)
        created_weather = []

        # Record genuine current weather entry
        w_rec = await weather_repo.record_current_weather(
            latitude=13.285588,
            longitude=79.296860,
            temperature_c=28.5,
            relative_humidity_pct=75.0,
            precipitation_mm=0.0,
            rain_mm=0.0,
            wind_speed_kmh=12.4,
            weather_code=1,
            weather_condition="Mainly clear",
            field_id=f01.id,
            provider="Open-Meteo",
            timezone_str="Asia/Kolkata",
        )
        await session.flush()
        created_weather.append(w_rec.id)

        # Check cached retrieval
        cached = await weather_repo.get_cached_current_weather(13.285588, 79.296860, max_age_minutes=30)
        assert cached is not None
        assert float(cached.temperature_c) == 28.5
        assert cached.weather_condition == "Mainly clear"
        print(f"  [PASS] Retrieved cached weather record: Temp={cached.temperature_c}°C, Condition='{cached.weather_condition}'")

        # Clean up test weather record
        for wid in created_weather:
            await session.execute(delete(WeatherRecord).where(WeatherRecord.id == wid))
        await session.commit()
        print("  [PASS] Controlled test weather record cleaned up; table pristine.")

    from app.db.session import close_db_engine
    await close_db_engine()


def run_http_tests(base_url: str):
    """Runs HTTP-level integration tests against the live Uvicorn server."""
    print("\n" + "=" * 70)
    print("PART 2: LIVE HTTP API INTEGRATION TESTS")
    print("=" * 70)

    # 1. Database connectivity endpoint
    print("\n[HTTP 1] GET /health/database...")
    r = requests.get(f"{base_url}/health/database", timeout=5.0)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    db_json = r.json()
    assert db_json["status"] == "healthy"
    assert db_json["connected"] is True
    assert db_json["database"] == "paddy_farming_db"
    print(f"  [PASS] GET /health/database -> 200 OK (Latency: {db_json.get('latency_ms')}ms)")

    # 2. Fields list from PostgreSQL
    print("\n[HTTP 2] GET /fields (PostgreSQL Data Source)...")
    r = requests.get(f"{base_url}/fields", timeout=5.0)
    assert r.status_code == 200
    fields_data = r.json()
    assert fields_data["total_fields"] == 58, f"Expected 58 fields, got {fields_data['total_fields']}"
    assert len(fields_data["fields"]) == 58
    assert fields_data["fields"][0]["field_id"] == "FIELD_01"
    print(f"  [PASS] GET /fields -> 200 OK (58 fields, first={fields_data['fields'][0]['field_id']})")

    # 3. Retrieve FIELD_01
    print("\n[HTTP 3] GET /fields/FIELD_01...")
    r = requests.get(f"{base_url}/fields/FIELD_01", timeout=5.0)
    assert r.status_code == 200
    f01 = r.json()
    assert f01["external_field_id"] == "FIELD_01"
    assert f01["latitude"] == 13.285588
    assert f01["longitude"] == 79.296860
    assert f01["observation_count"] == 10
    print(f"  [PASS] GET /fields/FIELD_01 -> 200 OK (Name: {f01['field_name']}, Obs: {f01['observation_count']})")

    # 4 & 5. Retrieve all observations for FIELD_01
    print("\n[HTTP 4 & 5] GET /fields/FIELD_01/timeseries (10 Observations, Features, Ordering)...")
    r = requests.get(f"{base_url}/fields/FIELD_01/timeseries", timeout=5.0)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    ts = r.json()
    assert ts["field_id"] == "FIELD_01"
    assert ts["total_timesteps"] == 10
    assert len(ts["timesteps"]) == 10
    assert ts["features"] == ["NDVI", "NDRE", "GNDVI"]
    assert ts["coordinates"]["latitude"] == 13.285588
    assert ts["coordinates"]["longitude"] == 79.296860
    assert ts["has_dates"] is True
    print(f"  [PASS] GET /fields/FIELD_01/timeseries -> 200 OK (10 timesteps, dates present)")

    # 6. Retrieve another valid field
    print("\n[HTTP 6] GET /fields/FIELD_58/timeseries...")
    r = requests.get(f"{base_url}/fields/FIELD_58/timeseries", timeout=5.0)
    assert r.status_code == 200
    ts58 = r.json()
    assert ts58["field_id"] == "FIELD_58"
    assert ts58["total_timesteps"] == 10
    print("  [PASS] GET /fields/FIELD_58/timeseries -> 200 OK (10 timesteps)")

    # 7. Request unknown field 404 behavior
    print("\n[HTTP 7] Unknown Field 404 Behavior...")
    r = requests.get(f"{base_url}/fields/FIELD_99", timeout=5.0)
    assert r.status_code == 404, f"Expected 404 for /fields/FIELD_99, got {r.status_code}"
    r_ts = requests.get(f"{base_url}/fields/FIELD_99/timeseries", timeout=5.0)
    assert r_ts.status_code == 404, f"Expected 404 for /fields/FIELD_99/timeseries, got {r_ts.status_code}"
    print("  [PASS] Nonexistent field correctly returned HTTP 404 on both endpoints.")

    # 9. Pagination via query parameters
    print("\n[HTTP 9] GET /fields with pagination (?skip=10&limit=5)...")
    r = requests.get(f"{base_url}/fields?skip=10&limit=5", timeout=5.0)
    assert r.status_code == 200
    p_data = r.json()
    assert len(p_data["fields"]) == 5
    assert p_data["total_fields"] == 58
    assert p_data["fields"][0]["field_id"] == "FIELD_11"
    print(f"  [PASS] Pagination: skip=10, limit=5 -> returned {len(p_data['fields'])} items (first: {p_data['fields'][0]['field_id']})")

    # 15. Database unavailable simulation
    print("\n[HTTP 15] Database Unavailable Behavior Simulation...")
    with patch("app.db.session.check_db_connectivity") as mock_conn:
        mock_conn.return_value = {
            "status": "unhealthy",
            "connected": False,
            "error": "Connection to PostgreSQL refused",
        }
        r_unhealthy = requests.get(f"{base_url}/health/database", timeout=5.0)
        assert r_unhealthy.status_code == 503, f"Expected 503, got {r_unhealthy.status_code}"
        assert r_unhealthy.json()["status"] == "unhealthy"
        print("  [PASS] GET /health/database returned HTTP 503 when DB connectivity failed.")

    # 16. Existing image-only prediction regression
    print("\n[HTTP 16] Regression: POST /predict (Image-Only Disease Detection + Persistence)...")
    img_path = BACKEND_DIR / "test_images" / "tungro" / "TUNGRO5_67.JPG"
    if not img_path.exists():
        found = list(BACKEND_DIR.glob("test_images/**/*.jpg")) + list(BACKEND_DIR.glob("test_images/**/*.JPG"))
        assert found, "No test images found"
        img_path = found[0]

    with open(img_path, "rb") as f:
        r_pred = requests.post(
            f"{base_url}/predict",
            files={"file": (img_path.name, f, "image/jpeg")},
            data={"field_id": "FIELD_01", "question": "Are these leaf tips infected?"},
            timeout=15.0,
        )
    assert r_pred.status_code == 200, f"Expected 200, got {r_pred.status_code}: {r_pred.text}"
    pred_res = r_pred.json()
    assert "disease" in pred_res
    assert "confidence" in pred_res
    assert "prediction_id" in pred_res, "Expected persisted prediction_id in response"
    pred_uuid = pred_res["prediction_id"]
    print(f"  [PASS] POST /predict: disease='{pred_res['disease']}', conf={pred_res['confidence']:.4f}, prediction_id={pred_uuid}")

    # Query the persisted prediction via GET /predictions/{prediction_id}
    r_check = requests.get(f"{base_url}/predictions/{pred_uuid}", timeout=5.0)
    assert r_check.status_code == 200
    p_record = r_check.json()
    assert p_record["id"] == pred_uuid
    assert p_record["prediction_mode"] == "image_only"
    assert p_record["predicted_disease"] == pred_res["disease"]
    print(f"  [PASS] Verified persisted record via GET /predictions/{pred_uuid}")

    # 17. Existing multimodal prediction regression
    print("\n[HTTP 17] Regression: POST /predict/multimodal (Cross-Attention + Persistence)...")
    with open(img_path, "rb") as f:
        r_mm = requests.post(
            f"{base_url}/predict/multimodal",
            files={"file": (img_path.name, f, "image/jpeg")},
            data={"field_id": "FIELD_01"},
            timeout=20.0,
        )
    assert r_mm.status_code == 200, f"Expected 200, got {r_mm.status_code}: {r_mm.text}"
    mm_res = r_mm.json()
    assert mm_res["prediction_mode"] == "multimodal"
    assert "predicted_class" in mm_res
    assert mm_res["predicted_class"] in config.MULTIMODAL_CLASSES
    assert len(mm_res["top_3_predictions"]) == 3
    assert len(mm_res["temporal_attention_weights"]) == 10
    assert "prediction_id" in mm_res
    mm_uuid = mm_res["prediction_id"]
    print(f"  [PASS] POST /predict/multimodal: class='{mm_res['predicted_class']}', conf={mm_res['confidence']:.4f}, prediction_id={mm_uuid}")

    # Query persisted multimodal prediction
    r_mm_check = requests.get(f"{base_url}/predictions/{mm_uuid}", timeout=5.0)
    assert r_mm_check.status_code == 200
    mm_record = r_mm_check.json()
    assert mm_record["id"] == mm_uuid
    assert mm_record["prediction_mode"] == "multimodal"
    print(f"  [PASS] Verified persisted multimodal record via GET /predictions/{mm_uuid}")

    # 18. Grad-CAM and SHAP regression
    print("\n[HTTP 18] Regression: Grad-CAM and SHAP Visual Explanations...")
    with open(img_path, "rb") as f:
        r_cam = requests.post(
            f"{base_url}/explain/gradcam",
            files={"file": (img_path.name, f, "image/jpeg")},
            data={"target_class": "tungro"},
            timeout=15.0,
        )
    assert r_cam.status_code == 200, f"Grad-CAM failed: {r_cam.status_code}: {r_cam.text}"
    assert "overlay_image" in r_cam.json()
    print("  [PASS] POST /explain/gradcam -> 200 OK (overlay_image generated)")

    with open(img_path, "rb") as f:
        r_shap = requests.post(
            f"{base_url}/explain/shap",
            files={"file": (img_path.name, f, "image/jpeg")},
            data={"field_id": "FIELD_01", "nsamples": 10},
            timeout=30.0,
        )
    assert r_shap.status_code == 200, f"SHAP failed: {r_shap.status_code}: {r_shap.text}"
    assert "timestep_attributions" in r_shap.json()
    print("  [PASS] POST /explain/shap -> 200 OK (temporal timestep_attributions generated)")

    # 19. Weather endpoint regression
    print("\n[HTTP 19] Regression: Weather Endpoints (Current, Forecast, Field Weather)...")
    r_w_curr = requests.get(
        f"{base_url}/weather/current?latitude=13.285588&longitude=79.296860",
        timeout=25.0,
    )
    assert r_w_curr.status_code == 200
    assert "current" in r_w_curr.json()
    print(f"  [PASS] GET /weather/current -> 200 OK (Temp: {r_w_curr.json()['current']['temperature']}°C)")

    r_w_fc = requests.get(
        f"{base_url}/weather/forecast?latitude=13.285588&longitude=79.296860&forecast_days=3",
        timeout=25.0,
    )
    assert r_w_fc.status_code == 200
    assert len(r_w_fc.json()["daily_forecast"]) == 3
    print(f"  [PASS] GET /weather/forecast -> 200 OK (3 days forecast)")

    r_w_field = requests.get(
        f"{base_url}/fields/FIELD_01/weather?forecast_days=3",
        timeout=25.0,
    )
    assert r_w_field.status_code == 200
    assert r_w_field.json()["field_id"] == "FIELD_01"
    print(f"  [PASS] GET /fields/FIELD_01/weather -> 200 OK")

    # 20. Field health endpoint regression
    print("\n[HTTP 20] Regression: GET /fields/FIELD_01/health...")
    r_fh = requests.get(f"{base_url}/fields/FIELD_01/health", timeout=5.0)
    assert r_fh.status_code == 200
    fh_json = r_fh.json()
    assert fh_json["field_id"] == "FIELD_01"
    assert "advisory_summary" in fh_json
    assert "latest_indices" in fh_json
    assert "changes_and_trends" in fh_json
    print(f"  [PASS] GET /fields/FIELD_01/health -> 200 OK (Advisory: {fh_json['advisory_summary'][:60]}...)")

    return [pred_uuid, mm_uuid]


def clean_persisted_predictions(prediction_ids):
    """Synchronous cleanup helper using asyncio to clean regression prediction records."""
    async def _clean():
        from app.db.session import AsyncSessionLocal, close_db_engine
        async with AsyncSessionLocal() as session:
            for pid_str in prediction_ids:
                try:
                    pid = uuid.UUID(pid_str)
                    await session.execute(delete(PredictionHistory).where(PredictionHistory.id == pid))
                except Exception:
                    pass
            await session.commit()
        await close_db_engine()
    asyncio.run(_clean())


def main():
    print("=" * 70)
    print("PADDY FARMING ASSISTANT - STEP 11F.8 EXHAUSTIVE INTEGRATION TEST SUITE")
    print("=" * 70)

    # Run repository async tests first
    asyncio.run(run_async_tests())

    # Start Uvicorn test server
    print("\n[Setup] Starting live FastAPI Uvicorn test server on port 8003...")
    server = ServerThread(port=8003)
    server.start()
    base_url = "http://127.0.0.1:8003"
    persisted_ids = []

    try:
        if not wait_for_server(base_url, timeout=25.0):
            raise RuntimeError("FastAPI test server failed to start within 25 seconds.")
        print(f"  [OK] Server online at {base_url}")

        # Run live HTTP tests
        persisted_ids = run_http_tests(base_url)

        print("\n" + "=" * 70)
        print("ALL 20 STEP 11F.8 TEST CRITERIA PASSED SUCCESSFULLY (PASS)")
        print("=" * 70)

    finally:
        print("\n[Teardown] Stopping FastAPI test server...")
        server.stop()
        if persisted_ids:
            clean_persisted_predictions(persisted_ids)
            print("  [OK] Test prediction records cleaned up.")


if __name__ == "__main__":
    main()
