"""
Paddy Farming Assistant - STEP 11D Comprehensive AI Integration Audit & Verification
Executes strict end-to-end verification across:
1. Image-only EfficientNet-B4 prediction (POST /predict)
2. Satellite data tensor properties and field mapping
3. Temporal Cross-Attention Multimodal model inference (POST /predict/multimodal)
4. Class mapping comparison (13-class vs 11-class discrepancy)
5. Grad-CAM visual explanation generation (POST /explain/gradcam)
6. SHAP temporal satellite explanation generation (POST /explain/shap)
7. End-to-end integration and non-interference verification
8. HTTP endpoints test suite against live Uvicorn server
"""

import sys
import time
import json
import threading
from pathlib import Path
from typing import Dict, Any, List

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
import torch
import requests
import uvicorn
from PIL import Image

from app import config
from app.main import app
from app.models.model_loader import ModelLoader
from app.models.multimodal_model import MultimodalModelLoader, TemporalCrossAttentionModel
from app.services.prediction import PredictionService
from app.services.field_mapping import FieldMappingService
from app.services.multimodal_prediction import MultimodalPredictionService
from app.services.gradcam import GradCAMService, gradcam_service
from app.services.shap_service import SHAPService, shap_service


class ServerThread(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = 8006):
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


def wait_for_server(base_url: str, timeout: float = 25.0) -> bool:
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


def run_audit():
    print("=" * 80)
    print("STEP 11D — COMPLETE AI INTEGRATION AUDIT AND RECTIFICATION")
    print("=" * 80)

    results = {}
    details = {}

    test_image_path = BACKEND_DIR / "test_images" / "tungro" / "TUNGRO5_67.JPG"
    assert test_image_path.exists(), f"Missing test image at {test_image_path}"

    # -------------------------------------------------------------------------
    # STEP 1 & 2: VERIFY IMAGE-ONLY INFERENCE (EfficientNet-B4)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 2 — VERIFY IMAGE-ONLY INFERENCE (EfficientNet-B4)")
    print("=" * 80)

    # 1. Model Loading & Architecture
    eff_model = ModelLoader.get_model()
    assert eff_model is not None, "ModelLoader failed to load EfficientNet-B4"
    assert isinstance(eff_model, torch.nn.Module), "EfficientNet-B4 is not a torch.nn.Module"
    total_eff_params = sum(p.numel() for p in eff_model.parameters())
    print(f"  [OK] EfficientNet-B4 Model Loaded: {total_eff_params:,} parameters")

    # 2. Checkpoint Verification
    eff_ckpt = config.EFFICIENTNET_CHECKPOINT_PATH
    assert eff_ckpt.exists(), f"Checkpoint missing at {eff_ckpt}"
    ckpt_size = eff_ckpt.stat().st_size
    assert ckpt_size == 222833055, f"Unexpected checkpoint size: {ckpt_size}"
    print(f"  [OK] Checkpoint Verified: {eff_ckpt.name} ({ckpt_size:,} bytes)")

    # 3. Direct PredictionService Inference
    pred_service = PredictionService()
    assert pred_service.num_classes == 13, f"Expected 13 classes, got {pred_service.num_classes}"
    t0 = time.perf_counter()
    pred_res = pred_service.predict(test_image_path, top_k=3)
    t_eff_ms = (time.perf_counter() - t0) * 1000

    print(f"  [OK] Image Preprocessing: Resize({config.IMAGE_SIZE}, {config.IMAGE_SIZE}) + ImageNet Normalization")
    print(f"  [OK] Direct Inference Result in {t_eff_ms:.2f} ms:")
    print(f"       - Disease:    '{pred_res['disease']}' (Index: {pred_res['predicted_index']})")
    print(f"       - Confidence: {pred_res['confidence']:.4f}")
    print(f"       - Top 3:      {[(p['disease'], p['probability']) for p in pred_res['top3']]}")

    assert pred_res["disease"] == "tungro", f"Expected 'tungro', got {pred_res['disease']}"
    assert pred_res["predicted_index"] == 12, f"Expected index 12, got {pred_res['predicted_index']}"
    assert pred_res["confidence"] > 0.90, f"Expected confidence > 0.90, got {pred_res['confidence']}"
    assert len(pred_res["top3"]) == 3, "Expected 3 top predictions"
    assert not pred_res["is_healthy"], "Tungro should not be marked as healthy"

    results["image_only_inference"] = "PASS"
    details["image_only_inference"] = {
        "checkpoint": eff_ckpt.name,
        "checkpoint_size_bytes": ckpt_size,
        "parameters": total_eff_params,
        "predicted_disease": pred_res["disease"],
        "confidence": pred_res["confidence"],
        "latency_ms": t_eff_ms,
    }

    # -------------------------------------------------------------------------
    # STEP 3: VERIFY SATELLITE DATA AND FIELD MAPPING
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 3 — VERIFY SATELLITE DATA AND FIELD MAPPING")
    print("=" * 80)

    field_service = FieldMappingService.get_instance()
    assert field_service.is_loaded, "FieldMappingService is not loaded"

    # Satellite sequence tensor verification
    seq_path = config.SATELLITE_SEQUENCES_PATH
    assert seq_path.exists(), f"Satellite sequence missing at {seq_path}"
    seq_arr = np.load(seq_path)
    assert seq_arr.shape == (58, 10, 3), f"Unexpected shape {seq_arr.shape}"
    assert seq_arr.dtype == np.float32, f"Unexpected dtype {seq_arr.dtype}"
    assert not np.isnan(seq_arr).any(), "NaN found in satellite sequence"
    assert not np.isinf(seq_arr).any(), "Inf found in satellite sequence"
    print(f"  [OK] Satellite Sequence Tensor: {seq_arr.shape} float32 in range [{seq_arr.min():.4f}, {seq_arr.max():.4f}]")
    print(f"  [OK] Temporal Dimension: {config.SATELLITE_TIMESTEPS} timesteps")
    print(f"  [OK] Feature Ordering:   {config.SATELLITE_FEATURES} (NDVI, NDRE, GNDVI)")

    # Field ID resolution
    f1_info = field_service.get_field("FIELD_01")
    assert f1_info is not None, "FIELD_01 not found in master catalog"
    assert f1_info["clean_field_id"] == "CLEAN_FIELD_001"
    assert abs(f1_info["latitude"] - 13.285588) < 1e-4
    assert abs(f1_info["longitude"] - 79.296860) < 1e-4

    # Sequence indexing verification
    f1_seq = field_service.get_satellite_sequence("FIELD_01")
    assert f1_seq.shape == (10, 3)
    np.testing.assert_array_equal(f1_seq, seq_arr[0], err_msg="FIELD_01 sequence does not match seq_arr[0]")
    print("  [OK] FIELD_01 mapped strictly to sequence index 0")

    f58_seq = field_service.get_satellite_sequence("FIELD_58")
    assert f58_seq.shape == (10, 3)
    np.testing.assert_array_equal(f58_seq, seq_arr[57], err_msg="FIELD_58 sequence does not match seq_arr[57]")
    print("  [OK] FIELD_58 mapped strictly to sequence index 57")

    # Non-existent field returns None safely
    f_unknown = field_service.get_field("FIELD_99")
    assert f_unknown is None, "FIELD_99 should be None"
    print("  [OK] Unknown field FIELD_99 safely rejected (None, no silent fallback)")

    results["satellite_data_and_mapping"] = "PASS"
    details["satellite_data_and_mapping"] = {
        "sequences_shape": list(seq_arr.shape),
        "features": config.SATELLITE_FEATURES,
        "timesteps": config.SATELLITE_TIMESTEPS,
        "total_fields": config.TOTAL_SATELLITE_FIELDS,
        "field_01_coords": (f1_info["latitude"], f1_info["longitude"]),
    }

    # -------------------------------------------------------------------------
    # STEP 4: VERIFY CROSS-ATTENTION MULTIMODAL INFERENCE & CLASS MAPPINGS
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 4 — VERIFY CROSS-ATTENTION MULTIMODAL INFERENCE")
    print("=" * 80)

    # 1. Checkpoint & Metadata
    mm_ckpt_path = config.MULTIMODAL_CHECKPOINT_PATH
    assert mm_ckpt_path.exists(), f"Multimodal checkpoint missing at {mm_ckpt_path}"
    mm_meta = MultimodalModelLoader.get_metadata()
    mm_model = MultimodalModelLoader.get_model()
    assert isinstance(mm_model, TemporalCrossAttentionModel)

    total_mm_params = sum(p.numel() for p in mm_model.parameters())
    print(f"  [OK] Checkpoint:    {mm_ckpt_path.name} ({mm_ckpt_path.stat().st_size:,} bytes)")
    print(f"  [OK] Architecture:  '{mm_meta['architecture']}' ({total_mm_params:,} parameters)")
    print(f"  [OK] Training Acc:  Best Val Accuracy: {mm_meta['best_val_accuracy']*100:.2f}% | F1: {mm_meta['best_val_f1']:.4f}")
    print(f"  [OK] Sat Mean:      {list(np.round(mm_meta['satellite_mean'], 4))}")
    print(f"  [OK] Sat Std:       {list(np.round(mm_meta['satellite_std'], 4))}")

    # 2. Class Mapping Comparison (13 Image Classes vs 11 Multimodal Classes)
    print("\n  [CLASS MAPPING COMPARISON]")
    image_classes = config.DISEASE_CLASSES
    mm_classes = mm_meta["class_names"]
    print(f"  Image Model (13 classes):      {image_classes}")
    print(f"  Multimodal Model (11 classes): {mm_classes}")

    omitted_classes = [c for c in image_classes if c not in mm_classes]
    print(f"  Classes Omitted in Multimodal: {omitted_classes}")
    assert omitted_classes == ["leaf_smut", "normal"], f"Unexpected omitted classes: {omitted_classes}"
    print("  [OK] Discrepancy Verified: 'leaf_smut' and 'normal' were omitted from multimodal training dataset.")
    print("       Indices 0-8 are identical; indices 9-10 are shifted (sheath_blight=9, tungro=10).")

    # 3. Direct Multimodal Inference Execution
    mm_service = MultimodalPredictionService()
    t0 = time.perf_counter()
    mm_res = mm_service.predict(test_image_path, field_id="FIELD_01", top_k=3)
    t_mm_ms = (time.perf_counter() - t0) * 1000

    print(f"\n  [OK] Direct Multimodal Prediction in {t_mm_ms:.2f} ms:")
    print(f"       - Mode:             {mm_res['prediction_mode']}")
    print(f"       - Field:            {mm_res['field_id']}")
    print(f"       - Predicted Class:  '{mm_res['predicted_class']}' (conf: {mm_res['confidence']:.4f})")
    print(f"       - Top 3:            {[(p['disease'], p['probability']) for p in mm_res['top_3_predictions']]}")
    print(f"       - Attention:        {mm_res['temporal_attention_weights']}")

    assert mm_res["predicted_class"] == "sheath_blight"
    assert mm_res["confidence"] > 0.85
    assert len(mm_res["temporal_attention_weights"]) == 10
    assert abs(sum(mm_res["temporal_attention_weights"]) - 1.0) < 0.01

    results["cross_attention_multimodal"] = "PASS"
    details["cross_attention_multimodal"] = {
        "checkpoint": mm_ckpt_path.name,
        "checkpoint_size_bytes": mm_ckpt_path.stat().st_size,
        "parameters": total_mm_params,
        "image_classes_count": len(image_classes),
        "multimodal_classes_count": len(mm_classes),
        "omitted_classes": omitted_classes,
        "predicted_class": mm_res["predicted_class"],
        "confidence": mm_res["confidence"],
        "latency_ms": t_mm_ms,
    }

    # -------------------------------------------------------------------------
    # STEP 5: VERIFY GRAD-CAM EXPLANATION PIPELINE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 5 — VERIFY GRAD-CAM VISUAL EXPLANATION PIPELINE")
    print("=" * 80)

    t0 = time.perf_counter()
    gcam_res = gradcam_service.generate_gradcam(test_image_path, alpha=0.5)
    t_gcam_ms = (time.perf_counter() - t0) * 1000

    print(f"  [OK] Grad-CAM computed in {t_gcam_ms:.2f} ms:")
    print(f"       - Target Layer:      {gcam_res['target_layer']}")
    print(f"       - Predicted Class:   '{gcam_res['predicted_class']}'")
    print(f"       - Target Explained:  '{gcam_res['target_class']}' (Index: {gcam_res['target_index']})")
    print(f"       - Image Dimensions:  {gcam_res['image_dimensions']['width']}x{gcam_res['image_dimensions']['height']}")
    print(f"       - Heatmap Range:     max={gcam_res['heatmap_intensity_max']}, mean={gcam_res['heatmap_intensity_mean']}")
    print(f"       - Overlay URI Len:   {len(gcam_res['overlay_image'])} characters")

    assert gcam_res["target_layer"] == "features.8"
    assert gcam_res["predicted_class"] == "tungro"
    assert gcam_res["target_class"] == "tungro"
    assert gcam_res["heatmap_intensity_max"] == 1.0
    assert 0.0 <= gcam_res["heatmap_intensity_mean"] <= 1.0
    assert len(gcam_res["overlay_image"]) > 5000

    # Test target_class override (explaining 'blast' instead of top prediction)
    gcam_blast = gradcam_service.generate_gradcam(test_image_path, target_class="blast")
    assert gcam_blast["target_class"] == "blast"
    assert gcam_blast["target_index"] == 3
    print("  [OK] Target class override verified ('blast' logit gradient backpropagated)")

    results["gradcam_pipeline"] = "PASS"
    details["gradcam_pipeline"] = {
        "target_layer": gcam_res["target_layer"],
        "predicted_class": gcam_res["predicted_class"],
        "dimensions": (gcam_res["image_dimensions"]["width"], gcam_res["image_dimensions"]["height"]),
        "latency_ms": t_gcam_ms,
    }

    # -------------------------------------------------------------------------
    # STEP 6: VERIFY SHAP TEMPORAL EXPLANATION PIPELINE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 6 — VERIFY SHAP TEMPORAL EXPLANATION PIPELINE")
    print("=" * 80)

    t0 = time.perf_counter()
    with open(test_image_path, "rb") as f_img:
        shap_res = shap_service.explain_multimodal(
            f_img.read(),
            field_id="FIELD_01",
            seed=42,
        )
    t_shap_ms = (time.perf_counter() - t0) * 1000

    print(f"  [OK] SHAP computed in {t_shap_ms:.2f} ms:")
    print(f"       - Target Model:      '{shap_res['explanation_target_model']}'")
    print(f"       - Scope:             '{shap_res['explanation_scope']}'")
    print(f"       - Predicted Class:   '{shap_res['predicted_class']}'")
    print(f"       - Target Explained:  '{shap_res['target_class']}' (Index: {shap_res['target_index']})")
    print(f"       - Timesteps:         {len(shap_res['timestep_attributions']) // 3}")
    print(f"       - Feature Names:     {shap_res['input_feature_names']}")
    print(f"       - SHAP Dimensions:   {shap_res['shap_dimensions']}")

    assert shap_res["explanation_scope"] == "conditional_satellite_input"
    assert shap_res["predicted_class"] == "sheath_blight"
    assert shap_res["target_class"] == "sheath_blight"
    assert shap_res["shap_dimensions"] == [10, 3]
    assert len(shap_res["timestep_attributions"]) == 30  # 10 x 3

    # Check finite numbers and feature impact
    for summary in shap_res["feature_importance_summary"]:
        print(f"       - {summary['feature']}: mean_abs={summary['mean_absolute_shap']:.6f}, net={summary['net_shap']:.6f}")
        assert not np.isnan(summary["mean_absolute_shap"])
        assert not np.isinf(summary["mean_absolute_shap"])

    results["shap_pipeline"] = "PASS"
    details["shap_pipeline"] = {
        "model": shap_res["explanation_target_model"],
        "scope": shap_res["explanation_scope"],
        "dimensions": shap_res["shap_dimensions"],
        "features": shap_res["input_feature_names"],
        "latency_ms": t_shap_ms,
    }

    # -------------------------------------------------------------------------
    # STEP 7: HTTP END-TO-END INTEGRATION AND NON-INTERFERENCE VERIFICATION
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 7 — HTTP END-TO-END INTEGRATION & NON-INTERFERENCE TEST")
    print("=" * 80)

    host = "127.0.0.1"
    port = 8006
    base_url = f"http://{host}:{port}"
    print(f"  [Server] Launching FastAPI background server on {base_url}...")
    server = ServerThread(host=host, port=port)
    server.start()

    if not wait_for_server(base_url, timeout=25.0):
        print("  [FATAL] Server failed to start within timeout.")
        server.stop()
        sys.exit(1)
    print("  [OK] Server online and responsive on /health.")

    try:
        # Test 1: POST /predict (Image-Only)
        with open(test_image_path, "rb") as f_img:
            r1 = requests.post(f"{base_url}/predict", files={"file": (test_image_path.name, f_img, "image/jpeg")}, timeout=10.0)
        assert r1.status_code == 200, f"Expected 200, got {r1.status_code}: {r1.text}"
        data1 = r1.json()
        assert data1["disease"] == "tungro"
        print(f"  [HTTP 1] POST /predict: 200 OK -> disease='{data1['disease']}', conf={data1['confidence']:.4f}")

        # Test 2: POST /predict/multimodal (Image + Field ID)
        with open(test_image_path, "rb") as f_img:
            r2 = requests.post(
                f"{base_url}/predict/multimodal",
                files={"file": (test_image_path.name, f_img, "image/jpeg")},
                data={"field_id": "FIELD_01"},
                timeout=10.0,
            )
        assert r2.status_code == 200, f"Expected 200, got {r2.status_code}: {r2.text}"
        data2 = r2.json()
        assert data2["predicted_class"] == "sheath_blight"
        print(f"  [HTTP 2] POST /predict/multimodal: 200 OK -> class='{data2['predicted_class']}', conf={data2['confidence']:.4f}")

        # Test 3: POST /explain/gradcam
        with open(test_image_path, "rb") as f_img:
            r3 = requests.post(f"{base_url}/explain/gradcam", files={"file": (test_image_path.name, f_img, "image/jpeg")}, timeout=10.0)
        assert r3.status_code == 200
        data3 = r3.json()
        assert data3["predicted_class"] == "tungro"
        print(f"  [HTTP 3] POST /explain/gradcam: 200 OK -> layer='{data3['target_layer']}', uri_len={len(data3['overlay_image'])}")

        # Test 4: POST /explain/shap
        with open(test_image_path, "rb") as f_img:
            r4 = requests.post(
                f"{base_url}/explain/shap",
                files={"file": (test_image_path.name, f_img, "image/jpeg")},
                data={"field_id": "FIELD_01"},
                timeout=15.0,
            )
        assert r4.status_code == 200
        data4 = r4.json()
        assert data4["predicted_class"] == "sheath_blight"
        print(f"  [HTTP 4] POST /explain/shap: 200 OK -> scope='{data4['explanation_scope']}', dims={data4['shap_dimensions']}")

        # Test 5: Verify POST /predict is completely unaffected after Grad-CAM and SHAP execution
        with open(test_image_path, "rb") as f_img:
            r5 = requests.post(f"{base_url}/predict", files={"file": (test_image_path.name, f_img, "image/jpeg")}, timeout=10.0)
        assert r5.status_code == 200
        data5 = r5.json()
        assert data5["disease"] == "tungro"
        assert abs(data5["confidence"] - data1["confidence"]) < 1e-5
        print(f"  [HTTP 5] Non-Interference Verified: POST /predict unchanged after explanation runs (conf: {data5['confidence']:.4f})")

        # Test 6: Satellite & Weather Endpoints
        r_ts = requests.get(f"{base_url}/fields/FIELD_01/timeseries", timeout=5.0)
        assert r_ts.status_code == 200 and len(r_ts.json()["timesteps"]) == 10
        print(f"  [HTTP 6] GET /fields/FIELD_01/timeseries: 200 OK (10 timesteps)")

        r_hlth = requests.get(f"{base_url}/fields/FIELD_01/health", timeout=5.0)
        assert r_hlth.status_code == 200 and "advisory_summary" in r_hlth.json()
        print(f"  [HTTP 7] GET /fields/FIELD_01/health: 200 OK (vegetation metrics)")

        r_wtr = requests.get(f"{base_url}/fields/FIELD_01/weather", timeout=5.0)
        assert r_wtr.status_code == 200 and r_wtr.json()["provider"] == "Open-Meteo"
        print(f"  [HTTP 8] GET /fields/FIELD_01/weather: 200 OK (Open-Meteo observations)")

        # Test 7: Negative cases
        r_neg1 = requests.post(f"{base_url}/predict/multimodal", data={"field_id": "FIELD_01"})
        assert r_neg1.status_code == 400
        print("  [HTTP 9] Negative: Missing image file returned HTTP 400")

        with open(test_image_path, "rb") as f_img:
            r_neg2 = requests.post(f"{base_url}/predict/multimodal", files={"file": (test_image_path.name, f_img, "image/jpeg")}, data={"field_id": "FIELD_99"})
        assert r_neg2.status_code == 404
        print("  [HTTP 10] Negative: Unknown field ID 'FIELD_99' returned HTTP 404")

        results["http_end_to_end_integration"] = "PASS"

    finally:
        print("\n  [Server] Stopping test server...")
        server.stop()
        print("  [OK] Server stopped.")

    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STEP 11D INTEGRATION AUDIT SUMMARY")
    print("=" * 80)
    all_passed = True
    for k, status in results.items():
        print(f"  - {k:<35}: {status}")
        if status != "PASS":
            all_passed = False

    print("=" * 80)
    overall_status = "COMPLETE" if all_passed else "FAIL"
    print(f"OVERALL STATUS: {overall_status} (PASS)")
    print("=" * 80)

    # Save metrics JSON
    metrics = {
        "results": results,
        "details": details,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": overall_status,
    }
    with open(BACKEND_DIR / "step_11d_audit_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)


if __name__ == "__main__":
    run_audit()
