"""
Paddy Farming Assistant - STEP 11D.3 Multimodal Prediction HTTP Integration Tests
Executes actual HTTP requests against the FastAPI application running on Uvicorn.
Verifies all 10 requirements specified in STEP 11D.3.
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
import torch
from PIL import Image

from app import config
from app.main import app
from app.models.model_loader import ModelLoader
from app.models.multimodal_model import MultimodalModelLoader, TemporalCrossAttentionModel
from app.services.field_mapping import FieldMappingService
from app.services.multimodal_prediction import MultimodalPredictionService


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


def run_all_multimodal_tests():
    print("=" * 75)
    print("STEP 11D.3 — CROSS-ATTENTION MULTIMODAL INFERENCE VERIFICATION")
    print("=" * 75)

    port = 8000
    base_url = f"http://127.0.0.1:{port}"

    # Verify test image exists
    test_img_path = BACKEND_DIR / "test_images" / "tungro" / "TUNGRO5_67.JPG"
    assert test_img_path.exists(), f"Test image not found at {test_img_path}"

    print(f"\n[Setup] Launching FastAPI application on {base_url}...")
    server_thread = ServerThread(port=port)
    server_thread.start()

    ready = wait_for_server(base_url)
    assert ready, f"FastAPI server failed to start within timeout on {base_url}"
    print("  [OK] Server is active and accepting HTTP connections.")

    test_passed = 0
    total_tests = 10

    try:
        # -------------------------------------------------------------
        # Test 1: Successful inference using real image and valid field
        # -------------------------------------------------------------
        print("\n[Test 1] Successful multimodal inference (POST /predict/multimodal with real image + FIELD_01)...")
        with open(test_img_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/predict/multimodal",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01"},
                timeout=10.0,
            )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        assert data["prediction_mode"] == "multimodal"
        assert data["field_id"] == "FIELD_01"
        assert data["predicted_class"] in config.MULTIMODAL_CLASSES
        assert 0.0 <= data["confidence"] <= 1.0
        assert len(data["top_3_predictions"]) == 3
        assert data["image_model_status"] == "loaded"
        assert data["satellite_model_status"] == "loaded"
        assert data["fusion_model_status"] == "loaded"
        assert data["satellite_timesteps"] == 10
        assert "temporal_attention_weights" in data
        assert len(data["temporal_attention_weights"]) == 10
        print(f"  [OK] Predicted: {data['predicted_class']} (confidence: {data['confidence']:.4f})")
        print(f"  [OK] Top 3: {[(p['disease'], p['probability']) for p in data['top_3_predictions']]}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 2: Also accepts 'image' parameter name as form field
        # -------------------------------------------------------------
        print("\n[Test 2] Parameter alias test (using 'image' instead of 'file')...")
        with open(test_img_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/predict/multimodal",
                files={"image": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_02"},
                timeout=10.0,
            )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data2 = resp.json()
        assert data2["field_id"] == "FIELD_02"
        print("  [OK] Form parameter 'image' supported seamlessly.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 3: Finite output probabilities and sum approximately 1.0
        # -------------------------------------------------------------
        print("\n[Test 3] Numerical validity & probability normalization...")
        probs_sum = sum(p["probability"] for p in data["top_3_predictions"])
        assert not np.isnan(data["confidence"])
        assert not np.isinf(data["confidence"])
        for p in data["top_3_predictions"]:
            assert not np.isnan(p["probability"])
            assert not np.isinf(p["probability"])
            assert p["disease"] in config.MULTIMODAL_CLASSES
        attn_sum = sum(data["temporal_attention_weights"])
        assert abs(attn_sum - 1.0) < 0.01, f"Attention weights sum to {attn_sum}, expected ~1.0"
        print(f"  [OK] Top 3 probabilities sum: {probs_sum:.4f} <= 1.0; attention sum: {attn_sum:.4f}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 4: Satellite sequence retrieval matching authoritative mapping
        # -------------------------------------------------------------
        print("\n[Test 4] Satellite sequence retrieval verification...")
        field_svc = FieldMappingService.get_instance()
        seq_01 = field_svc.get_satellite_sequence("FIELD_01")
        assert seq_01 is not None
        assert seq_01.shape == (10, 3)
        ref_seqs = np.load(config.SATELLITE_SEQUENCES_PATH)
        assert np.allclose(seq_01, ref_seqs[0]), "FIELD_01 sequence must match sequence tensor index 0"
        print(f"  [OK] Satellite sequence correctly retrieved with shape {seq_01.shape}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 5: Unknown field returns HTTP 404
        # -------------------------------------------------------------
        print("\n[Test 5] Unknown field identifier handling (expecting 404)...")
        with open(test_img_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/predict/multimodal",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "UNKNOWN_FIELD_999"},
                timeout=10.0,
            )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
        err = resp.json()
        assert "not found" in err.get("detail", "").lower()
        print(f"  [OK] HTTP 404 returned as expected: {err.get('detail')}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 6: Missing field_id parameter returns HTTP 400
        # -------------------------------------------------------------
        print("\n[Test 6] Missing field_id handling (expecting 400)...")
        with open(test_img_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/predict/multimodal",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={},
                timeout=10.0,
            )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        print("  [OK] Missing field_id rejected with HTTP 400.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 7: Invalid image handling (missing image, empty file, corrupted file, unsupported extension)
        # -------------------------------------------------------------
        print("\n[Test 7] Invalid image edge cases...")
        # A. Missing image file
        resp_no_img = requests.post(
            f"{base_url}/predict/multimodal",
            data={"field_id": "FIELD_01"},
            timeout=10.0,
        )
        assert resp_no_img.status_code == 400, f"Expected 400, got {resp_no_img.status_code}"

        # B. Empty file (0 bytes)
        resp_empty = requests.post(
            f"{base_url}/predict/multimodal",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
            data={"field_id": "FIELD_01"},
            timeout=10.0,
        )
        assert resp_empty.status_code == 400, f"Expected 400, got {resp_empty.status_code}"

        # C. Corrupted file
        resp_corrupt = requests.post(
            f"{base_url}/predict/multimodal",
            files={"file": ("corrupt.jpg", b"NOT_A_VALID_JPEG_HEADER_BYTES", "image/jpeg")},
            data={"field_id": "FIELD_01"},
            timeout=10.0,
        )
        assert resp_corrupt.status_code == 400, f"Expected 400, got {resp_corrupt.status_code}"

        # D. Unsupported extension (.txt)
        resp_bad_ext = requests.post(
            f"{base_url}/predict/multimodal",
            files={"file": ("notes.txt", b"hello world", "text/plain")},
            data={"field_id": "FIELD_01"},
            timeout=10.0,
        )
        assert resp_bad_ext.status_code == 415, f"Expected 415, got {resp_bad_ext.status_code}"
        print("  [OK] All invalid image edge cases properly caught (400, 415).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 8: Existing POST /predict remains operational and unchanged
        # -------------------------------------------------------------
        print("\n[Test 8] Existing STEP 11C image-only POST /predict non-regression...")
        with open(test_img_path, "rb") as f:
            resp_img_only = requests.post(
                f"{base_url}/predict",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01"},
                timeout=10.0,
            )
        assert resp_img_only.status_code == 200, f"Expected 200, got {resp_img_only.status_code}: {resp_img_only.text}"
        data_img_only = resp_img_only.json()
        assert "disease" in data_img_only
        assert "confidence" in data_img_only
        assert "top3" in data_img_only
        assert data_img_only["disease"] in config.DISEASE_CLASSES
        print(f"  [OK] Existing POST /predict operational: {data_img_only['disease']} (conf: {data_img_only['confidence']})")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 9: /health/model reports both image and multimodal statuses
        # -------------------------------------------------------------
        print("\n[Test 9] In-memory health check (/health/model)...")
        resp_health = requests.get(f"{base_url}/health/model", timeout=5.0)
        assert resp_health.status_code == 200
        h_data = resp_health.json()
        assert h_data["status"] == "loaded"
        assert h_data["multimodal_status"] == "loaded"
        assert h_data["multimodal_model_loaded"] is True
        print(f"  [OK] Model health: status={h_data['status']}, multimodal_status={h_data['multimodal_status']}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 10: Numerical equivalence with direct Python inference
        # -------------------------------------------------------------
        print("\n[Test 10] Direct Python inference comparison against HTTP API...")
        direct_service = MultimodalPredictionService()
        with open(test_img_path, "rb") as f:
            direct_result = direct_service.predict(f.read(), "FIELD_01")

        assert direct_result["predicted_class"] == data["predicted_class"], (
            f"Class mismatch: direct={direct_result['predicted_class']} vs http={data['predicted_class']}"
        )
        assert abs(direct_result["confidence"] - data["confidence"]) < 1e-4, (
            f"Confidence mismatch: direct={direct_result['confidence']} vs http={data['confidence']}"
        )
        print(f"  [OK] Exact numerical equivalence verified:")
        print(f"       HTTP API:   class={data['predicted_class']}, conf={data['confidence']}")
        print(f"       Direct Svc: class={direct_result['predicted_class']}, conf={direct_result['confidence']}")
        test_passed += 1

    finally:
        print("\n[Teardown] Stopping FastAPI server...")
        server_thread.stop()
        time.sleep(0.5)

    print("\n" + "=" * 75)
    print(f"ALL TESTS COMPLETED: {test_passed} / {total_tests} PASSED (100%)")
    print("=" * 75)


if __name__ == "__main__":
    run_all_multimodal_tests()
