"""
Paddy Farming Assistant - STEP 11D.5 Grad-CAM HTTP Integration Tests
Executes actual HTTP requests against the FastAPI application running on Uvicorn.
Verifies all 10 requirements specified in STEP 11D.5.
"""

import sys
import time
import io
import base64
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
from PIL import Image

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


def run_gradcam_tests():
    print("=" * 75)
    print("STEP 11D.5 — GRAD-CAM VISUALIZATION HTTP ENDPOINT VERIFICATION")
    print("=" * 75)

    port = 8000
    base_url = f"http://127.0.0.1:{port}"

    test_img_path = BACKEND_DIR / "test_images" / "tungro" / "TUNGRO5_67.JPG"
    assert test_img_path.exists(), f"Test image not found at {test_img_path}"

    with Image.open(test_img_path) as img:
        orig_w, orig_h = img.size
        orig_arr = np.array(img.convert("RGB"))

    print(f"\n[Setup] Launching FastAPI application on {base_url}...")
    server_thread = ServerThread(port=port)
    server_thread.start()

    ready = wait_for_server(base_url)
    assert ready, f"FastAPI server failed to start within timeout on {base_url}"
    print("  [OK] Server is active and accepting HTTP connections.")

    test_passed = 0
    total_tests = 11

    try:
        # -------------------------------------------------------------
        # Test 1: Valid Leaf Image Produces Real Grad-CAM Visualization
        # -------------------------------------------------------------
        print("\n[Test 1] Testing POST /explain/gradcam with valid leaf image...")
        with open(test_img_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/explain/gradcam",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                timeout=15.0,
            )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        assert data["status"] == "success"
        assert data["predicted_class"] == "tungro"
        assert data["target_class"] == "tungro"
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["target_layer"] == "features.8"
        assert "overlay_image" in data
        assert data["overlay_image"].startswith("data:image/jpeg;base64,")
        assert data["media_type"] == "image/jpeg"
        assert "limitations_note" in data
        print(f"  [OK] Grad-CAM computed for '{data['predicted_class']}' (conf: {data['confidence']:.4f}).")
        print(f"  [OK] Base64 overlay generated (len: {len(data['overlay_image'])}).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 2: Visualization Dimensions Match Original Image Dimensions
        # -------------------------------------------------------------
        print("\n[Test 2] Verifying overlay dimensions match original image exactly...")
        assert data["image_dimensions"]["width"] == orig_w
        assert data["image_dimensions"]["height"] == orig_h

        # Decode base64 JPEG and inspect image dimensions
        b64_data = data["overlay_image"].split(",")[1]
        decoded_bytes = base64.b64decode(b64_data)
        decoded_img = Image.open(io.BytesIO(decoded_bytes))
        assert decoded_img.size == (orig_w, orig_h), (
            f"Dimension mismatch: got {decoded_img.size}, expected ({orig_w}, {orig_h})"
        )
        print(f"  [OK] Overlay dimensions ({decoded_img.size[0]}x{decoded_img.size[1]}) match original ({orig_w}x{orig_h}).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 3: Heatmap Contains Finite and Valid Normalized Values
        # -------------------------------------------------------------
        print("\n[Test 3] Verifying numerical bounds of heatmap intensities...")
        mean_int = data["heatmap_intensity_mean"]
        max_int = data["heatmap_intensity_max"]
        assert not np.isnan(mean_int) and not np.isinf(mean_int)
        assert not np.isnan(max_int) and not np.isinf(max_int)
        assert 0.0 <= mean_int <= 1.0
        assert 0.0 <= max_int <= 1.0
        assert max_int >= mean_int
        print(f"  [OK] Heatmap intensity bounds: mean={mean_int:.4f}, max={max_int:.4f} in [0.0, 1.0].")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 4: Predicted Class Index Matches Existing Class Mapping
        # -------------------------------------------------------------
        print("\n[Test 4] Verifying class mapping consistency...")
        assert data["predicted_index"] == 12  # tungro is index 12 in 13-class mapping
        assert data["target_index"] == 12
        assert config.DISEASE_CLASSES[data["predicted_index"]] == "tungro"
        print(f"  [OK] Predicted index {data['predicted_index']} corresponds strictly to '{data['predicted_class']}'.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 5: Overlay is NOT an Unchanged Copy of Input
        # -------------------------------------------------------------
        print("\n[Test 5] Verifying overlay is genuinely altered by Grad-CAM heatmap...")
        overlay_arr = np.array(decoded_img.convert("RGB"))
        assert not np.array_equal(overlay_arr, orig_arr), "Overlay must not be identical to original image."
        diff = np.abs(overlay_arr.astype(float) - orig_arr.astype(float))
        mean_diff = diff.mean()
        assert mean_diff > 3.0, f"Expected significant visual alteration, got mean diff {mean_diff}"
        print(f"  [OK] Overlay differs significantly from original image (mean pixel diff: {mean_diff:.2f}).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 6: Target Class Override / Selection
        # -------------------------------------------------------------
        print("\n[Test 6] Testing target_class selection (explaining 'blast' instead of top prediction)...")
        with open(test_img_path, "rb") as f:
            resp_class = requests.post(
                f"{base_url}/explain/gradcam",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"target_class": "blast"},
                timeout=15.0,
            )
        assert resp_class.status_code == 200
        d_class = resp_class.json()
        assert d_class["predicted_class"] == "tungro"
        assert d_class["target_class"] == "blast"
        assert d_class["target_index"] == config.DISEASE_CLASSES.index("blast")
        print(f"  [OK] Target class selection supported: predicted='{d_class['predicted_class']}', explained='{d_class['target_class']}'.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 7: Direct Image Response (response_format='image')
        # -------------------------------------------------------------
        print("\n[Test 7] Testing direct image streaming (response_format='image')...")
        with open(test_img_path, "rb") as f:
            resp_img = requests.post(
                f"{base_url}/explain/gradcam",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"response_format": "image"},
                timeout=15.0,
            )
        assert resp_img.status_code == 200
        assert resp_img.headers["content-type"] == "image/jpeg"
        assert resp_img.headers.get("x-predicted-class") == "tungro"
        assert len(resp_img.content) > 5000
        direct_img = Image.open(io.BytesIO(resp_img.content))
        assert direct_img.size == (orig_w, orig_h)
        print(f"  [OK] Direct image/jpeg response verified ({len(resp_img.content)} bytes, {direct_img.size[0]}x{direct_img.size[1]}).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 8: Invalid Images & Target Class Rejection
        # -------------------------------------------------------------
        print("\n[Test 8] Invalid images and parameters edge cases...")
        # A. Missing image
        r_no_img = requests.post(f"{base_url}/explain/gradcam", timeout=5.0)
        assert r_no_img.status_code == 400

        # B. Empty file (0 bytes)
        r_empty = requests.post(
            f"{base_url}/explain/gradcam",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
            timeout=5.0,
        )
        assert r_empty.status_code == 400

        # C. Corrupted file
        r_corrupt = requests.post(
            f"{base_url}/explain/gradcam",
            files={"file": ("corrupt.jpg", b"BAD_DATA", "image/jpeg")},
            timeout=5.0,
        )
        assert r_corrupt.status_code == 400

        # D. Unsupported extension
        r_bad_ext = requests.post(
            f"{base_url}/explain/gradcam",
            files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
            timeout=5.0,
        )
        assert r_bad_ext.status_code == 415

        # E. Invalid target class
        with open(test_img_path, "rb") as f:
            r_bad_class = requests.post(
                f"{base_url}/explain/gradcam",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"target_class": "non_existent_disease_xyz"},
                timeout=5.0,
            )
        assert r_bad_class.status_code == 400
        print("  [OK] Edge cases properly rejected: missing (400), empty (400), corrupt (400), bad ext (415), invalid class (400).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 9: Non-Regression of Existing POST /predict (Image-Only)
        # -------------------------------------------------------------
        print("\n[Test 9] Non-regression check: POST /predict (Image-Only)...")
        with open(test_img_path, "rb") as f:
            r_pred = requests.post(
                f"{base_url}/predict",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                timeout=10.0,
            )
        assert r_pred.status_code == 200
        assert r_pred.json()["disease"] == "tungro"
        print(f"  [OK] POST /predict operational: {r_pred.json()['disease']} (conf: {r_pred.json()['confidence']}).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 10: Non-Regression of Existing POST /predict/multimodal
        # -------------------------------------------------------------
        print("\n[Test 10] Non-regression check: POST /predict/multimodal...")
        with open(test_img_path, "rb") as f:
            r_mm = requests.post(
                f"{base_url}/predict/multimodal",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01"},
                timeout=10.0,
            )
        assert r_mm.status_code == 200
        assert r_mm.json()["prediction_mode"] == "multimodal"
        print(f"  [OK] POST /predict/multimodal operational: {r_mm.json()['predicted_class']} (conf: {r_mm.json()['confidence']}).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 11: Non-Regression of GET /fields/{field_id}/timeseries & health
        # -------------------------------------------------------------
        print("\n[Test 11] Non-regression check: Satellite time-series and field health...")
        r_ts = requests.get(f"{base_url}/fields/FIELD_01/timeseries", timeout=5.0)
        assert r_ts.status_code == 200 and r_ts.json()["total_timesteps"] == 10

        r_fh = requests.get(f"{base_url}/fields/FIELD_01/health", timeout=5.0)
        assert r_fh.status_code == 200 and r_fh.json()["health_classification_status"] == "unvalidated"

        print("  [OK] GET /fields/FIELD_01/timeseries -> 200")
        print("  [OK] GET /fields/FIELD_01/health -> 200")
        test_passed += 1

    finally:
        print("\n[Teardown] Stopping FastAPI server...")
        server_thread.stop()
        time.sleep(0.5)

    print("\n" + "=" * 75)
    print(f"ALL TESTS COMPLETED: {test_passed} / {total_tests} PASSED (100%)")
    print("=" * 75)


if __name__ == "__main__":
    run_gradcam_tests()
