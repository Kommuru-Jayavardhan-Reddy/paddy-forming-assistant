"""
Paddy Farming Assistant - STEP 11D.4 Field Health HTTP Integration Tests
Executes actual HTTP requests against the FastAPI application running on Uvicorn.
Verifies all requirements specified in STEP 11D.4.
"""

import sys
import time
import threading
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend directory is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
import requests
import uvicorn

from app import config
from app.main import app
from app.services.field_mapping import FieldMappingService
from app.services.field_health import FieldHealthService


class ServerThread(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
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


def run_field_health_tests():
    print("=" * 75)
    print("STEP 11D.4 — FIELD HEALTH HTTP ENDPOINT VERIFICATION")
    print("=" * 75)

    port = 8000
    base_url = f"http://127.0.0.1:{port}"

    test_img_path = BACKEND_DIR / "test_images" / "tungro" / "TUNGRO5_67.JPG"
    assert test_img_path.exists(), f"Test image not found at {test_img_path}"

    print(f"\n[Setup] Launching FastAPI application on {base_url}...")
    server_thread = ServerThread(port=port)
    server_thread.start()

    ready = wait_for_server(base_url)
    assert ready, f"FastAPI server failed to start within timeout on {base_url}"
    print("  [OK] Server is active and accepting HTTP connections.")

    test_passed = 0
    total_tests = 7

    try:
        # Load raw stored sequences for mathematical ground-truth checks
        raw_sequences = np.load(config.SATELLITE_SEQUENCES_PATH)
        assert raw_sequences.shape == (58, 10, 3)

        # -------------------------------------------------------------
        # Test 1: Valid Field Health Request (GET /fields/FIELD_01/health)
        # -------------------------------------------------------------
        print("\n[Test 1] Testing GET /fields/FIELD_01/health...")
        url = f"{base_url}/fields/FIELD_01/health"
        resp = requests.get(url, timeout=5.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        assert data["field_id"] == "FIELD_01"
        assert data["observation_count"] == 10
        assert data["latest_observation_date"] is not None
        assert data["previous_observation_date"] is not None
        assert "latest_indices" in data
        assert "previous_indices" in data
        assert "changes_and_trends" in data
        assert "summary_statistics" in data
        assert "data_quality_status" in data
        assert data["health_classification_status"] == "unvalidated"
        assert data["health_category"] is None
        assert len(data["limitations_and_interpretation_notes"]) >= 3
        print(f"  [OK] Response structure confirmed for FIELD_01.")
        print(f"       Advisory summary: {data['advisory_summary']}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 2: Correct Latest Values vs Stored Satellite Sequences
        # -------------------------------------------------------------
        print("\n[Test 2] Numerical precision vs stored satellite sequence array...")
        # FIELD_01 is index 0; latest is timestep 9 (0-indexed)
        expected_ndvi_01 = round(float(raw_sequences[0, 9, 0]), 4)
        expected_ndre_01 = round(float(raw_sequences[0, 9, 1]), 4)
        expected_gndvi_01 = round(float(raw_sequences[0, 9, 2]), 4)

        assert data["latest_indices"]["ndvi"] == expected_ndvi_01, (
            f"NDVI mismatch: got {data['latest_indices']['ndvi']}, expected {expected_ndvi_01}"
        )
        assert data["latest_indices"]["ndre"] == expected_ndre_01, (
            f"NDRE mismatch: got {data['latest_indices']['ndre']}, expected {expected_ndre_01}"
        )
        assert data["latest_indices"]["gndvi"] == expected_gndvi_01, (
            f"GNDVI mismatch: got {data['latest_indices']['gndvi']}, expected {expected_gndvi_01}"
        )

        # Cross-check FIELD_58 (index 57)
        resp_58 = requests.get(f"{base_url}/fields/FIELD_58/health", timeout=5.0)
        assert resp_58.status_code == 200
        data_58 = resp_58.json()
        expected_ndvi_58 = round(float(raw_sequences[57, 9, 0]), 4)
        assert data_58["latest_indices"]["ndvi"] == expected_ndvi_58
        print(f"  [OK] Latest indices match bilstm_sequences.npy ground truth:")
        print(f"       FIELD_01: NDVI={expected_ndvi_01}, NDRE={expected_ndre_01}, GNDVI={expected_gndvi_01}")
        print(f"       FIELD_58: NDVI={expected_ndvi_58}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 3: Correct Latest and Preceding Observation Dates
        # -------------------------------------------------------------
        print("\n[Test 3] Observation dates verification...")
        assert data["latest_observation_date"] == "2026-09-29", (
            f"Expected latest date 2026-09-29, got {data['latest_observation_date']}"
        )
        assert data["previous_observation_date"] == "2026-09-14", (
            f"Expected preceding date 2026-09-14, got {data['previous_observation_date']}"
        )
        print(f"  [OK] Latest date: {data['latest_observation_date']}, Previous date: {data['previous_observation_date']}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 4: Correct Trend & Change Calculations
        # -------------------------------------------------------------
        print("\n[Test 4] Trend and delta calculations verification...")
        for feat in ["ndvi", "ndre", "gndvi"]:
            metric = data["changes_and_trends"][feat]
            lat = metric["latest"]
            prev = metric["previous"]
            baseline = metric["baseline_first"]

            expected_abs = round(lat - prev, 4)
            assert metric["absolute_change"] == expected_abs, (
                f"{feat} abs change mismatch: {metric['absolute_change']} vs {expected_abs}"
            )

            expected_overall = round(lat - baseline, 4)
            assert metric["overall_change"] == expected_overall, (
                f"{feat} overall change mismatch: {metric['overall_change']} vs {expected_overall}"
            )

            if prev > 0:
                expected_pct = round(((lat - prev) / prev) * 100.0, 2)
                assert metric["percentage_change"] == expected_pct, (
                    f"{feat} pct change mismatch: {metric['percentage_change']} vs {expected_pct}"
                )

            assert metric["direction"] in ("increasing", "decreasing", "stable")
            assert "vegetation index trend" in metric["trend_description"].lower()

            stats = data["summary_statistics"][feat]
            assert stats["min"] <= stats["mean"] <= stats["max"]
            print(f"  [OK] {feat.upper()}: latest={lat}, prev={prev}, delta={expected_abs:+.4f}, "
                  f"pct={metric['percentage_change']}%, dir={metric['direction']}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 5: Safe Data Quality Status & Unvalidated Health Classification
        # -------------------------------------------------------------
        print("\n[Test 5] Data quality status & health categorization transparency...")
        dq = data["data_quality_status"]
        assert dq["total_observations"] == 10
        assert dq["valid_observations"] == 10
        assert dq["is_complete"] is True
        assert dq["has_anomalies"] is False
        assert "linear temporal interpolation" in dq["interpolation_note"].lower()

        assert data["health_classification_status"] == "unvalidated"
        assert data["health_category"] is None
        print("  [OK] Data completeness verified: 10/10 valid observations.")
        print("  [OK] Fixed categorical classification transparently marked 'unvalidated'.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 6: Unknown Field Returns HTTP 404
        # -------------------------------------------------------------
        print("\n[Test 6] Unknown field identifier handling (expecting HTTP 404)...")
        r_404_a = requests.get(f"{base_url}/fields/FIELD_99/health", timeout=5.0)
        assert r_404_a.status_code == 404, f"Expected 404, got {r_404_a.status_code}"
        assert "not found" in r_404_a.json().get("detail", "").lower()

        r_404_b = requests.get(f"{base_url}/fields/UNKNOWN_FIELD_XYZ/health", timeout=5.0)
        assert r_404_b.status_code == 404, f"Expected 404, got {r_404_b.status_code}"
        print(f"  [OK] Unknown field 'FIELD_99' returned HTTP 404: {r_404_a.json()['detail']}")
        print(f"  [OK] Unknown field 'UNKNOWN_FIELD_XYZ' returned HTTP 404: {r_404_b.json()['detail']}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 7: Non-Regression of All Existing Endpoints
        # -------------------------------------------------------------
        print("\n[Test 7] Regression verification of all existing endpoints...")
        # A. GET /health
        r_h = requests.get(f"{base_url}/health", timeout=5.0)
        assert r_h.status_code == 200 and r_h.json()["status"] == "healthy"

        # B. GET /health/model
        r_hm = requests.get(f"{base_url}/health/model", timeout=5.0)
        assert r_hm.status_code == 200 and r_hm.json()["status"] == "loaded"

        # C. GET /classes
        r_c = requests.get(f"{base_url}/classes", timeout=5.0)
        assert r_c.status_code == 200 and r_c.json()["total_classes"] == 13

        # D. GET /fields/FIELD_01/timeseries
        r_ts = requests.get(f"{base_url}/fields/FIELD_01/timeseries", timeout=5.0)
        assert r_ts.status_code == 200 and r_ts.json()["total_timesteps"] == 10

        # E. POST /predict (image-only)
        with open(test_img_path, "rb") as f:
            r_p = requests.post(
                f"{base_url}/predict",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01"},
                timeout=10.0,
            )
        assert r_p.status_code == 200 and "disease" in r_p.json()

        # F. POST /predict/multimodal
        with open(test_img_path, "rb") as f:
            r_mm = requests.post(
                f"{base_url}/predict/multimodal",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01"},
                timeout=10.0,
            )
        assert r_mm.status_code == 200
        mm_data = r_mm.json()
        assert mm_data["prediction_mode"] == "multimodal"
        assert mm_data["predicted_class"] in config.MULTIMODAL_CLASSES

        print("  [OK] /health -> 200 healthy")
        print("  [OK] /health/model -> 200 (both models loaded)")
        print("  [OK] /classes -> 200 (13 classes)")
        print("  [OK] /fields/FIELD_01/timeseries -> 200 (10 timesteps)")
        print(f"  [OK] POST /predict -> 200 (disease: {r_p.json()['disease']}, conf: {r_p.json()['confidence']})")
        print(f"  [OK] POST /predict/multimodal -> 200 (class: {mm_data['predicted_class']}, conf: {mm_data['confidence']})")
        test_passed += 1

    finally:
        print("\n[Teardown] Stopping FastAPI server...")
        server_thread.stop()
        time.sleep(0.5)

    print("\n" + "=" * 75)
    print(f"ALL TESTS COMPLETED: {test_passed} / {total_tests} PASSED (100%)")
    print("=" * 75)


if __name__ == "__main__":
    run_field_health_tests()
