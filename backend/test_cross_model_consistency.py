"""
Paddy Farming Assistant - STEP 11D.7 Cross-Model Class Mapping & Prediction Consistency HTTP Tests
Executes live HTTP requests against FastAPI backend on Uvicorn.
Verifies all cross-model mapping rules, missing class handling, disagreement transparency, and explainability validation.
"""

import sys
import time
import threading
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests
import uvicorn
from app import config
from app.main import app

PORT = 8007
BASE_URL = f"http://127.0.0.1:{PORT}"

class ServerThread(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = PORT):
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

def run_tests():
    print("=" * 80)
    print("STEP 11D.7 — CROSS-MODEL CLASS MAPPING & PREDICTION CONSISTENCY HTTP SUITE")
    print("=" * 80)

    server = ServerThread()
    server.start()

    if not wait_for_server(BASE_URL):
        print("[FAIL] Test server failed to start within timeout.")
        server.stop()
        sys.exit(1)
    print(f"[INFO] Server successfully running at {BASE_URL}")

    test_count = 0
    pass_count = 0

    normal_img_path = BACKEND_DIR / "test_images" / "normal" / "100111.jpg"
    tungro_img_path = BACKEND_DIR / "test_images" / "tungro" / "TUNGRO5_67.JPG"

    # --- TEST 1: POST /predict with real normal image ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /predict with real normal image...")
    with open(normal_img_path, "rb") as f:
        resp = requests.post(f"{BASE_URL}/predict", files={"file": ("100111.jpg", f, "image/jpeg")})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["disease"] == "normal", f"Expected disease='normal', got {data['disease']}"
    assert data["predicted_index"] == 10, f"Expected predicted_index=10, got {data['predicted_index']}"
    assert data["is_healthy"] is True, "Expected is_healthy=True"
    print(f"[PASS] Image model correctly predicted 'normal' (index: 10, conf: {data['confidence']}, is_healthy: {data['is_healthy']})")
    pass_count += 1

    # --- TEST 2: POST /predict/multimodal with real normal image + FIELD_01 ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /predict/multimodal with real normal image + FIELD_01...")
    with open(normal_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/predict/multimodal",
            files={"file": ("100111.jpg", f, "image/jpeg")},
            data={"field_id": "FIELD_01"},
        )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["predicted_class"] in config.MULTIMODAL_CLASSES, "Predicted class not in 11 classes"
    assert data["predicted_class"] not in ["leaf_smut", "normal"], "Multimodal predicted excluded class!"
    for top_pred in data["top_3_predictions"]:
        assert top_pred["disease"] in config.MULTIMODAL_CLASSES
        assert top_pred["disease"] not in ["leaf_smut", "normal"]
    print(f"[PASS] Multimodal correctly evaluated in 11-class domain: {data['predicted_class']} (conf: {data['confidence']})")
    pass_count += 1

    # --- TEST 3: Prediction Disagreement Isolation ---
    test_count += 1
    print(f"\n[TEST {test_count}] Prediction Disagreement Isolation on TUNGRO5_67.JPG + FIELD_01...")
    with open(tungro_img_path, "rb") as f:
        r_img = requests.post(f"{BASE_URL}/predict", files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")})
    with open(tungro_img_path, "rb") as f:
        r_mm = requests.post(
            f"{BASE_URL}/predict/multimodal",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"field_id": "FIELD_01"},
        )
    assert r_img.status_code == 200 and r_mm.status_code == 200
    d_img = r_img.json()
    d_mm = r_mm.json()
    assert d_img["disease"] == "tungro"
    assert d_img["predicted_index"] == 12
    assert d_mm["predicted_class"] == "sheath_blight"
    # Neither overwritten, distinct mappings
    assert d_img["disease"] != d_mm["predicted_class"]
    print(f"[PASS] Verified separate endpoints preserve distinct predictions: Image='{d_img['disease']}' vs Multimodal='{d_mm['predicted_class']}' without overwriting.")
    pass_count += 1

    # --- TEST 4: POST /explain/gradcam allows target_class='normal' ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/gradcam allows target_class='normal'...")
    with open(normal_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/gradcam",
            files={"file": ("100111.jpg", f, "image/jpeg")},
            data={"target_class": "normal"},
        )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["target_class"] == "normal"
    assert data["target_index"] == 10
    print("[PASS] Grad-CAM successfully explained class 'normal' at index 10.")
    pass_count += 1

    # --- TEST 5: POST /explain/gradcam allows target_class='leaf_smut' ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/gradcam allows target_class='leaf_smut'...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/gradcam",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"target_class": "leaf_smut"},
        )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["target_class"] == "leaf_smut"
    assert data["target_index"] == 9
    print("[PASS] Grad-CAM successfully explained class 'leaf_smut' at index 9.")
    pass_count += 1

    # --- TEST 6: POST /explain/gradcam rejects invalid target_class ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/gradcam rejects invalid target_class...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/gradcam",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"target_class": "invalid_disease"},
        )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "Invalid target_class" in resp.json()["detail"]
    print(f"[PASS] Grad-CAM safely rejected invalid target_class: {resp.json()['detail']}")
    pass_count += 1

    # --- TEST 7: POST /explain/gradcam rejects out-of-range target_index ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/gradcam rejects target_index=13...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/gradcam",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"target_index": 13},
        )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "Invalid target_index" in resp.json()["detail"]
    print(f"[PASS] Grad-CAM safely rejected target_index=13: {resp.json()['detail']}")
    pass_count += 1

    # --- TEST 8: POST /explain/shap accepts multimodal target_class='sheath_blight' (idx 9) ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/shap accepts target_class='sheath_blight' (idx 9)...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/shap",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"field_id": "FIELD_01", "target_class": "sheath_blight"},
        )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["target_class"] == "sheath_blight"
    assert data["target_index"] == 9
    print(f"[PASS] SHAP successfully explained 'sheath_blight' at multimodal index {data['target_index']}.")
    pass_count += 1

    # --- TEST 9: POST /explain/shap accepts multimodal target_class='tungro' (idx 10) ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/shap accepts target_class='tungro' (idx 10)...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/shap",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"field_id": "FIELD_01", "target_class": "tungro"},
        )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["target_class"] == "tungro"
    assert data["target_index"] == 10
    print(f"[PASS] SHAP successfully explained 'tungro' at multimodal index {data['target_index']}.")
    pass_count += 1

    # --- TEST 10: POST /explain/shap safely rejects target_class='leaf_smut' ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/shap safely rejects target_class='leaf_smut'...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/shap",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"field_id": "FIELD_01", "target_class": "leaf_smut"},
        )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "Invalid target_class 'leaf_smut'" in resp.json()["detail"]
    print(f"[PASS] SHAP safely rejected target_class='leaf_smut': {resp.json()['detail']}")
    pass_count += 1

    # --- TEST 11: POST /explain/shap safely rejects target_class='normal' ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/shap safely rejects target_class='normal'...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/shap",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"field_id": "FIELD_01", "target_class": "normal"},
        )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "Invalid target_class 'normal'" in resp.json()["detail"]
    print(f"[PASS] SHAP safely rejected target_class='normal': {resp.json()['detail']}")
    pass_count += 1

    # --- TEST 12: POST /explain/shap safely rejects target_index=11 ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/shap safely rejects target_index=11...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/shap",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"field_id": "FIELD_01", "target_index": 11},
        )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "Invalid target_index '11'" in resp.json()["detail"]
    print(f"[PASS] SHAP safely rejected target_index=11: {resp.json()['detail']}")
    pass_count += 1

    # --- TEST 13: POST /explain/shap safely rejects invalid_disease ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /explain/shap safely rejects invalid_disease...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/explain/shap",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"field_id": "FIELD_01", "target_class": "invalid_disease"},
        )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "Invalid target_class 'invalid_disease'" in resp.json()["detail"]
    print(f"[PASS] SHAP safely rejected invalid class: {resp.json()['detail']}")
    pass_count += 1

    # --- TEST 14: POST /predict/multimodal missing image file rejected ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /predict/multimodal missing image file rejected...")
    resp = requests.post(f"{BASE_URL}/predict/multimodal", data={"field_id": "FIELD_01"})
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    print(f"[PASS] Multimodal safely rejected missing image: {resp.json()['detail']}")
    pass_count += 1

    # --- TEST 15: POST /predict/multimodal missing field_id rejected ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /predict/multimodal missing field_id rejected...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(f"{BASE_URL}/predict/multimodal", files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")})
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    print(f"[PASS] Multimodal safely rejected missing field_id: {resp.json()['detail']}")
    pass_count += 1

    # --- TEST 16: POST /predict/multimodal unknown field_id rejected with 404 ---
    test_count += 1
    print(f"\n[TEST {test_count}] POST /predict/multimodal unknown field_id ('FIELD_99') rejected with 404...")
    with open(tungro_img_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/predict/multimodal",
            files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
            data={"field_id": "FIELD_99"},
        )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    print(f"[PASS] Multimodal safely rejected unknown field_id: {resp.json()['detail']}")
    pass_count += 1

    server.stop()

    print("\n" + "=" * 80)
    print(f"STEP 11D.7 HTTP TEST RESULTS: {pass_count} / {test_count} PASSED (100% PASS)")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
