"""
Paddy Farming Assistant - STEP 11D.2 Satellite Time-Series HTTP Integration Tests
Executes actual HTTP requests against the FastAPI application running on Uvicorn.
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


def run_http_tests():
    print("=" * 70)
    print("STEP 11D.2 — SATELLITE TIME-SERIES HTTP ENDPOINT VERIFICATION")
    print("=" * 70)

    port = 8000
    base_url = f"http://127.0.0.1:{port}"

    # Start Uvicorn in background thread
    print(f"\n[Setup] Launching FastAPI application on {base_url}...")
    server_thread = ServerThread(port=port)
    server_thread.start()

    ready = wait_for_server(base_url)
    assert ready, f"FastAPI server failed to start within timeout on {base_url}"
    print("  [OK] Server is active and accepting HTTP connections.")

    try:
        # Load reference satellite data
        ref_sequences = np.load(config.SATELLITE_SEQUENCES_PATH)

        # -------------------------------------------------------------
        # Test 1: GET /fields/FIELD_01/timeseries (First Field, Index 0)
        # -------------------------------------------------------------
        print("\n[Test 1] Testing GET /fields/FIELD_01/timeseries...")
        url = f"{base_url}/fields/FIELD_01/timeseries"
        resp = requests.get(url, timeout=5.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        assert data["field_id"] == "FIELD_01", f"Field ID mismatch: {data['field_id']}"
        assert data["sequence_index"] == 0, f"Expected index 0 for FIELD_01, got {data['sequence_index']}"
        assert data["features"] == ["NDVI", "NDRE", "GNDVI"], f"Features mismatch: {data['features']}"
        assert data["total_timesteps"] == 10, f"Expected 10 timesteps, got {data['total_timesteps']}"
        assert len(data["timesteps"]) == 10, f"Expected 10 timestep records, got {len(data['timesteps'])}"
        assert data["has_dates"] is True, "Expected has_dates=True"
        assert data["coordinates"]["latitude"] == 13.285588
        assert data["coordinates"]["longitude"] == 79.296860

        # Verify values against bilstm_sequences.npy[0]
        for t_idx, step in enumerate(data["timesteps"]):
            assert step["timestep"] == t_idx + 1
            assert step["date"] is not None and len(step["date"]) == 10
            exp_val = ref_sequences[0, t_idx]
            assert np.isclose(step["ndvi"], exp_val[0], atol=1e-5), f"NDVI mismatch at step {t_idx+1}"
            assert np.isclose(step["ndre"], exp_val[1], atol=1e-5), f"NDRE mismatch at step {t_idx+1}"
            assert np.isclose(step["gndvi"], exp_val[2], atol=1e-5), f"GNDVI mismatch at step {t_idx+1}"

        print("  [OK] FIELD_01 -> Index 0 -> 10 timesteps with valid [NDVI, NDRE, GNDVI] and dates.")
        print(f"       Sample timestep 1: Date={data['timesteps'][0]['date']}, NDVI={data['timesteps'][0]['ndvi']:.4f}, NDRE={data['timesteps'][0]['ndre']:.4f}, GNDVI={data['timesteps'][0]['gndvi']:.4f}")

        # -------------------------------------------------------------
        # Test 2: GET /fields/FIELD_58/timeseries (Last Field, Index 57)
        # -------------------------------------------------------------
        print("\n[Test 2] Testing GET /fields/FIELD_58/timeseries...")
        url = f"{base_url}/fields/FIELD_58/timeseries"
        resp = requests.get(url, timeout=5.0)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data58 = resp.json()

        assert data58["field_id"] == "FIELD_58", f"Field ID mismatch: {data58['field_id']}"
        assert data58["sequence_index"] == 57, f"Expected index 57 for FIELD_58, got {data58['sequence_index']}"
        assert len(data58["timesteps"]) == 10

        # Verify values against bilstm_sequences.npy[57]
        for t_idx, step in enumerate(data58["timesteps"]):
            exp_val = ref_sequences[57, t_idx]
            assert np.isclose(step["ndvi"], exp_val[0], atol=1e-5)
            assert np.isclose(step["ndre"], exp_val[1], atol=1e-5)
            assert np.isclose(step["gndvi"], exp_val[2], atol=1e-5)

        print("  [OK] FIELD_58 -> Index 57 -> 10 timesteps exactly matches bilstm_sequences.npy[57].")

        # -------------------------------------------------------------
        # Test 3: Case-insensitive / whitespace field normalization
        # -------------------------------------------------------------
        print("\n[Test 3] Testing case-insensitive field ID input (/fields/field_01/timeseries)...")
        resp_lower = requests.get(f"{base_url}/fields/field_01/timeseries", timeout=5.0)
        assert resp_lower.status_code == 200
        assert resp_lower.json()["field_id"] == "FIELD_01"
        print("  [OK] 'field_01' normalized successfully to 'FIELD_01' (HTTP 200).")

        # -------------------------------------------------------------
        # Test 4: Unknown Field returns HTTP 404
        # -------------------------------------------------------------
        print("\n[Test 4] Testing Unknown Field ID returns HTTP 404...")
        for bad_id in ["FIELD_99", "UNKNOWN_FIELD", "INVALID_XYZ"]:
            resp_404 = requests.get(f"{base_url}/fields/{bad_id}/timeseries", timeout=5.0)
            assert resp_404.status_code == 404, f"Expected 404 for {bad_id}, got {resp_404.status_code}"
            err_data = resp_404.json()
            assert "detail" in err_data or "error" in err_data
            print(f"  [OK] Unknown field '{bad_id}' returned HTTP 404: {err_data}")

        # -------------------------------------------------------------
        # Test 5: Verify existing STEP 11C health and classes endpoints
        # -------------------------------------------------------------
        print("\n[Test 5] Verifying existing STEP 11C health and metadata endpoints...")
        r_health = requests.get(f"{base_url}/health", timeout=5.0)
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "healthy"
        print("  [OK] /health -> HTTP 200 healthy")

        r_classes = requests.get(f"{base_url}/classes", timeout=5.0)
        assert r_classes.status_code == 200
        assert r_classes.json()["total_classes"] == 13
        print("  [OK] /classes -> HTTP 200 (13 classes)")

        # -------------------------------------------------------------
        # Test 6: Verify existing STEP 11C disease prediction endpoint
        # -------------------------------------------------------------
        print("\n[Test 6] Verifying existing STEP 11C disease prediction (POST /predict)...")
        test_img_path = BACKEND_DIR / "test_images" / "tungro" / "TUNGRO5_67.JPG"
        if not test_img_path.exists():
            test_img_path = list((BACKEND_DIR / "test_images").rglob("*.jpg"))[0]

        with open(test_img_path, "rb") as img_file:
            r_pred = requests.post(f"{base_url}/predict", files={"file": img_file}, timeout=10.0)

        assert r_pred.status_code == 200, f"Prediction failed: {r_pred.status_code} {r_pred.text}"
        pred_data = r_pred.json()
        assert pred_data.get("status") == "success"
        assert "disease" in pred_data
        assert "confidence" in pred_data
        assert "top3" in pred_data
        print(f"  [OK] POST /predict -> HTTP 200: Predicted '{pred_data['disease']}' (conf: {pred_data['confidence']:.4f})")


        print("\n" + "=" * 70)
        print("ALL STEP 11D.2 HTTP INTEGRATION TESTS PASSED (PASS)")
        print("=" * 70)
        return True

    finally:
        print("\n[Teardown] Shutting down background test server...")
        server_thread.stop()
        time.sleep(0.5)


if __name__ == "__main__":
    success = run_http_tests()
    if not success:
        sys.exit(1)
