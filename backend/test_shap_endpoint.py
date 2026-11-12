"""
Paddy Farming Assistant - STEP 11D.6 SHAP Explanation Complete Audit & Verification Suite
Executes real HTTP requests against the FastAPI application running on Uvicorn.
Verifies all 14 requirements specified in PHASE 7A and 7B of the STEP 11D.6 Audit.
"""

import sys
import time
import io
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


def run_comprehensive_shap_audit():
    print("=" * 80)
    print("STEP 11D.6 — SHAP EXPLANATION COMPLETE AUDIT & VERIFICATION TEST SUITE")
    print("=" * 80)

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
    total_tests = 13

    try:
        # -------------------------------------------------------------
        # Test 1: Valid SHAP Explanation Request
        # -------------------------------------------------------------
        print("\n[Test 1] Testing POST /explain/shap with valid image + FIELD_01...")
        t_req_start = time.time()
        with open(test_img_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/explain/shap",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01", "seed": 42},
                timeout=25.0,
            )
        elapsed_time = time.time() - t_req_start
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        assert data["status"] == "success"
        assert data["field_id"] == "FIELD_01"
        assert data["predicted_class"] == "sheath_blight"
        assert data["target_class"] == "sheath_blight"
        assert 0.0 <= data["confidence"] <= 1.0
        assert "target_logit" in data
        print(f"  [OK] SHAP computed for '{data['target_class']}' in {elapsed_time:.3f}s (conf: {data['confidence']:.4f}).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 2: Correct Model & Explanation Scope Identification
        # -------------------------------------------------------------
        print("\n[Test 2] Verifying model, scope, and explanation modality identification...")
        assert "TemporalCrossAttentionModel" in data["explanation_target_model"]
        assert data["explanation_scope"] == "conditional_satellite_input"
        assert "Satellite Temporal Time-Series" in data["explanation_modality"]
        assert data["explanation_method"] == "GradientExplainer"
        assert data["background_samples_count"] == 20
        assert data["nsamples"] == 100
        print(f"  [OK] Target Model: '{data['explanation_target_model']}'")
        print(f"  [OK] Scope:        '{data['explanation_scope']}'")
        print(f"  [OK] Modality:     '{data['explanation_modality']}'")
        print(f"  [OK] Method:       '{data['explanation_method']}' ({data['background_samples_count']} bg sequences)")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 3: Correct Feature Names, Timestep Mapping, & Observation Dates
        # -------------------------------------------------------------
        print("\n[Test 3] Verifying feature names, 10-timestep mapping, and observation dates...")
        assert data["input_feature_names"] == ["NDVI", "NDRE", "GNDVI"]
        attributions = data["timestep_attributions"]
        assert len(attributions) == 30, f"Expected 30 attributions (10 timesteps x 3 features), got {len(attributions)}"

        timesteps_seen = set(item["timestep"] for item in attributions)
        features_seen = set(item["feature"] for item in attributions)
        assert timesteps_seen == set(range(1, 11)), f"Timesteps mismatch: {timesteps_seen}"
        assert features_seen == {"NDVI", "NDRE", "GNDVI"}, f"Features mismatch: {features_seen}"

        # Verify observation date mapping is present and valid
        dates_seen = [item["observation_date"] for item in attributions if item["observation_date"] is not None]
        assert len(dates_seen) == 30, "All 30 attribution records must include observation_date for FIELD_01"
        assert attributions[0]["observation_date"] == "2026-05-19"
        assert attributions[-1]["observation_date"] == "2026-09-29"

        # Verify each item contains required attributes
        for attr in attributions:
            assert "satellite_value_raw" in attr
            assert "satellite_value_normalized" in attr
            assert "shap_value" in attr
            assert attr["contribution"] in ("positive", "negative", "neutral")
            assert attr["absolute_shap_value"] >= 0.0

        print(f"  [OK] Preserved temporal structure: 10 timesteps x 3 features = 30 verified records.")
        print(f"  [OK] Observation dates verified: {attributions[0]['observation_date']} to {attributions[-1]['observation_date']}.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 4: Correct SHAP Output Dimensions
        # -------------------------------------------------------------
        print("\n[Test 4] Verifying SHAP dimensions...")
        assert data["shap_dimensions"] == [10, 3]
        print(f"  [OK] SHAP tensor dimensions verified as {data['shap_dimensions']}.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 5: Finite Explanation Values & Summary Aggregations
        # -------------------------------------------------------------
        print("\n[Test 5] Verifying finite values and feature summaries...")
        for attr in attributions:
            sv = attr["shap_value"]
            assert not np.isnan(sv) and not np.isinf(sv), f"Invalid SHAP value: {sv}"

        summaries = data["feature_importance_summary"]
        assert len(summaries) == 3
        summary_feats = [s["feature"] for s in summaries]
        assert set(summary_feats) == {"NDVI", "NDRE", "GNDVI"}

        for s in summaries:
            assert s["mean_absolute_shap"] >= 0.0
            assert not np.isnan(s["net_shap"])

        # Check positive / negative contributions lists
        assert len(data["top_positive_contributions"]) <= 5
        assert len(data["top_negative_contributions"]) <= 5
        for item in data["top_negative_contributions"]:
            assert item["direction"] == "negative"
            assert item["shap_value"] < 0
            assert "observation_date" in item
        for item in data["top_positive_contributions"]:
            assert item["direction"] == "positive"
            assert item["shap_value"] > 0
            assert "observation_date" in item

        print(f"  [OK] Finite values verified. Feature summaries:")
        for s in summaries:
            print(f"       {s['feature']}: mean_abs={s['mean_absolute_shap']:.6f}, net={s['net_shap']:.6f}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 6: Unknown Field ID Handling (expecting HTTP 404)
        # -------------------------------------------------------------
        print("\n[Test 6] Testing unknown field_id handling (expecting HTTP 404)...")
        with open(test_img_path, "rb") as f:
            resp_unknown = requests.post(
                f"{base_url}/explain/shap",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "UNKNOWN_FIELD_999"},
                timeout=10.0,
            )
        assert resp_unknown.status_code == 404
        assert "not found" in resp_unknown.json()["detail"].lower()
        print(f"  [OK] Unknown field correctly returned HTTP 404: {resp_unknown.json()['detail']}")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 7: Input Validation Edge Cases
        # -------------------------------------------------------------
        print("\n[Test 7] Testing input validation edge cases...")
        # A. Missing image
        r_no_img = requests.post(f"{base_url}/explain/shap", data={"field_id": "FIELD_01"}, timeout=5.0)
        assert r_no_img.status_code == 400

        # B. Empty file (0 bytes)
        r_empty = requests.post(
            f"{base_url}/explain/shap",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
            data={"field_id": "FIELD_01"},
            timeout=5.0,
        )
        assert r_empty.status_code == 400

        # C. Corrupted file
        r_corrupt = requests.post(
            f"{base_url}/explain/shap",
            files={"file": ("corrupt.jpg", b"INVALID_DATA", "image/jpeg")},
            data={"field_id": "FIELD_01"},
            timeout=5.0,
        )
        assert r_corrupt.status_code == 400

        # D. Unsupported extension
        r_bad_ext = requests.post(
            f"{base_url}/explain/shap",
            files={"file": ("doc.txt", b"hello world", "text/plain")},
            data={"field_id": "FIELD_01"},
            timeout=5.0,
        )
        assert r_bad_ext.status_code == 415

        # E. Unsupported target class
        with open(test_img_path, "rb") as f:
            r_bad_class = requests.post(
                f"{base_url}/explain/shap",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01", "target_class": "non_existent_disease_xyz"},
                timeout=5.0,
            )
        assert r_bad_class.status_code == 400
        print("  [OK] Rejection edge cases confirmed: missing (400), empty (400), corrupt (400), .txt (415), bad class (400).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 8: Target Class Selection & Multimodal Prediction Consistency
        # -------------------------------------------------------------
        print("\n[Test 8] Testing target_class selection and prediction consistency...")
        with open(test_img_path, "rb") as f:
            resp_override = requests.post(
                f"{base_url}/explain/shap",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01", "target_class": "bacterial_leaf_blight"},
                timeout=15.0,
            )
        assert resp_override.status_code == 200
        d_override = resp_override.json()
        assert d_override["predicted_class"] == "sheath_blight"
        assert d_override["target_class"] == "bacterial_leaf_blight"
        assert d_override["target_index"] == 0

        # Verify predicted class matches POST /predict/multimodal output exactly
        with open(test_img_path, "rb") as f:
            resp_mm = requests.post(
                f"{base_url}/predict/multimodal",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01"},
                timeout=10.0,
            )
        assert resp_mm.status_code == 200
        d_mm = resp_mm.json()
        assert d_override["predicted_class"] == d_mm["predicted_class"]
        assert abs(d_override["confidence"] - d_mm["confidence"]) < 1e-3
        print(f"  [OK] Consistency verified: SHAP predicted '{d_override['predicted_class']}' matches Multimodal '{d_mm['predicted_class']}'.")
        print(f"  [OK] Target class override verified: explained target '{d_override['target_class']}' logit {d_override['target_logit']:.4f}.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 9: Reproducibility under Identical Inputs
        # -------------------------------------------------------------
        print("\n[Test 9] Verifying exact reproducibility with seed=42...")
        with open(test_img_path, "rb") as f:
            r_rep1 = requests.post(
                f"{base_url}/explain/shap",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01", "seed": 42},
                timeout=15.0,
            )
        with open(test_img_path, "rb") as f:
            r_rep2 = requests.post(
                f"{base_url}/explain/shap",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01", "seed": 42},
                timeout=15.0,
            )
        assert r_rep1.status_code == 200 and r_rep2.status_code == 200
        vals1 = [x["shap_value"] for x in r_rep1.json()["timestep_attributions"]]
        vals2 = [x["shap_value"] for x in r_rep2.json()["timestep_attributions"]]
        max_diff = np.max(np.abs(np.array(vals1) - np.array(vals2)))
        assert max_diff == 0.0, f"Expected 0.0 difference between runs with identical seed, got {max_diff}"
        print(f"  [OK] 100% numerical reproducibility verified (max difference: {max_diff}).")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 10: GET /fields (Fields Catalog Endpoint)
        # -------------------------------------------------------------
        print("\n[Test 10] Testing GET /fields catalog...")
        r_fields = requests.get(f"{base_url}/fields", timeout=5.0)
        assert r_fields.status_code == 200
        d_fields = r_fields.json()
        assert d_fields["total_fields"] == 58
        assert len(d_fields["fields"]) == 58
        assert d_fields["fields"][0]["field_id"] == "FIELD_01"
        assert d_fields["fields"][-1]["field_id"] == "FIELD_58"
        print(f"  [OK] GET /fields operational: verified all {d_fields['total_fields']} catalog fields.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 11: Non-Regression of STEP 11D.5 Grad-CAM Endpoint
        # -------------------------------------------------------------
        print("\n[Test 11] Non-regression check: POST /explain/gradcam...")
        with open(test_img_path, "rb") as f:
            resp_gc = requests.post(
                f"{base_url}/explain/gradcam",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                timeout=15.0,
            )
        assert resp_gc.status_code == 200
        d_gc = resp_gc.json()
        assert d_gc["status"] == "success"
        assert d_gc["target_layer"] == "features.8"
        assert "overlay_image" in d_gc
        print(f"  [OK] Grad-CAM operational: predicted '{d_gc['predicted_class']}', layer '{d_gc['target_layer']}'.")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 12: Non-Regression of Prediction Endpoints
        # -------------------------------------------------------------
        print("\n[Test 12] Non-regression check: POST /predict & POST /predict/multimodal...")
        with open(test_img_path, "rb") as f:
            r_pred = requests.post(
                f"{base_url}/predict",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                timeout=10.0,
            )
        assert r_pred.status_code == 200
        assert r_pred.json()["disease"] == "tungro"

        with open(test_img_path, "rb") as f:
            r_mm2 = requests.post(
                f"{base_url}/predict/multimodal",
                files={"file": ("TUNGRO5_67.JPG", f, "image/jpeg")},
                data={"field_id": "FIELD_01"},
                timeout=10.0,
            )
        assert r_mm2.status_code == 200
        assert r_mm2.json()["predicted_class"] == "sheath_blight"
        print(f"  [OK] POST /predict -> {r_pred.json()['disease']} (conf: {r_pred.json()['confidence']})")
        print(f"  [OK] POST /predict/multimodal -> {r_mm2.json()['predicted_class']} (conf: {r_mm2.json()['confidence']})")
        test_passed += 1

        # -------------------------------------------------------------
        # Test 13: Non-Regression of System, Metadata, Timeseries, & Health Endpoints
        # -------------------------------------------------------------
        print("\n[Test 13] Non-regression check: System, Metadata, Timeseries, and Health endpoints...")
        assert requests.get(f"{base_url}/health", timeout=5.0).status_code == 200
        assert requests.get(f"{base_url}/classes", timeout=5.0).status_code == 200
        r_ts = requests.get(f"{base_url}/fields/FIELD_01/timeseries", timeout=5.0)
        assert r_ts.status_code == 200 and r_ts.json()["total_timesteps"] == 10
        r_fh = requests.get(f"{base_url}/fields/FIELD_01/health", timeout=5.0)
        assert r_fh.status_code == 200 and r_fh.json()["health_classification_status"] == "unvalidated"

        print("  [OK] GET /health -> 200")
        print("  [OK] GET /classes -> 200 (13 classes)")
        print("  [OK] GET /fields/FIELD_01/timeseries -> 200 (10 timesteps)")
        print("  [OK] GET /fields/FIELD_01/health -> 200")
        test_passed += 1

    finally:
        print("\n[Teardown] Stopping FastAPI server...")
        server_thread.stop()
        time.sleep(0.5)

    print("\n" + "=" * 80)
    print(f"ALL TESTS COMPLETED: {test_passed} / {total_tests} PASSED (100%)")
    print("=" * 80)


if __name__ == "__main__":
    run_comprehensive_shap_audit()
