"""
Cross-Model Class Mapping and Prediction Consistency Verification Script
For STEP 11D.7 Audit
"""

import sys
import os
import json
import io
import torch
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app import config
from app.models.model_loader import ModelLoader
from app.models.multimodal_model import MultimodalModelLoader
from app.services.prediction import PredictionService
from app.services.multimodal_prediction import MultimodalPredictionService
from app.services.gradcam import GradCAMService
from app.services.shap_service import SHAPService

def test_class_mappings_against_training_artifacts():
    print("\n--- 1. Testing Class Mappings Against Training Artifacts ---")
    
    # 1. Image Model
    meta_path = Path("AI_model/step_1_to_4/STEP_4A_EfficientNet_B4_metadata.json")
    with open(meta_path, "r") as f:
        step4a_meta = json.load(f)
    step4a_classes = step4a_meta["classes"]
    
    assert config.DISEASE_CLASSES == step4a_classes, "Config DISEASE_CLASSES does not match Step 4A metadata!"
    assert len(config.DISEASE_CLASSES) == 13, f"Expected 13 classes, got {len(config.DISEASE_CLASSES)}"
    print("[PASS] Config DISEASE_CLASSES exactly matches Step 4A metadata (13 classes).")
    
    # 2. Multimodal Model
    mapping_txt = Path("AI_model/step_5_to_10/Step 7/text_and_csv_files_7/step7I_final_11class_mapping.txt")
    with open(mapping_txt, "r") as f:
        lines = f.readlines()
    parsed_11_classes = []
    for line in lines:
        if "->" in line:
            parts = line.strip().split("->")
            cls_name = parts[1].split()[0]
            parsed_11_classes.append(cls_name)
            
    assert config.MULTIMODAL_CLASSES == parsed_11_classes, "Config MULTIMODAL_CLASSES does not match Step 7I mapping text!"
    assert len(config.MULTIMODAL_CLASSES) == 11, f"Expected 11 classes, got {len(config.MULTIMODAL_CLASSES)}"
    print("[PASS] Config MULTIMODAL_CLASSES exactly matches Step 7I training mapping (11 classes).")
    
    # 3. Multimodal Checkpoint metadata
    mm_meta = MultimodalModelLoader.get_metadata()
    assert mm_meta["class_names"] == config.MULTIMODAL_CLASSES, "Checkpoint class_names does not match Config MULTIMODAL_CLASSES!"
    print("[PASS] Multimodal checkpoint metadata class_names matches Config MULTIMODAL_CLASSES.")
    
    # Check differences
    omitted = [c for c in config.DISEASE_CLASSES if c not in config.MULTIMODAL_CLASSES]
    assert omitted == ["leaf_smut", "normal"], f"Unexpected omitted classes: {omitted}"
    print(f"[PASS] Confirmed omitted classes in multimodal model: {omitted}")

def test_image_prediction_missing_classes():
    print("\n--- 2. Testing Missing-Class Handling (leaf_smut & normal) ---")
    pred_service = PredictionService()
    
    # 1. Real normal image
    normal_img_path = Path("backend/test_images/normal/100111.jpg")
    assert normal_img_path.exists(), "normal image missing!"
    res_normal = pred_service.predict(normal_img_path)
    print(f"Real normal image prediction: {res_normal['disease']} (index: {res_normal['predicted_index']}, conf: {res_normal['confidence']}, is_healthy: {res_normal['is_healthy']})")
    assert res_normal["predicted_index"] in range(13), "Index out of range"
    assert res_normal["disease"] == config.DISEASE_CLASSES[res_normal["predicted_index"]]
    print("[PASS] Real normal image evaluated and mapped correctly using 13-class mapping.")
    
    # 2. Mocked unit test for leaf_smut (index 9)
    # Using controlled test double
    fake_logits = torch.full((1, 13), -10.0)
    fake_logits[0, 9] = 10.0 # leaf_smut
    
    mock_model = MagicMock()
    mock_model.return_value = fake_logits
    with patch("app.models.model_loader.ModelLoader.get_model", return_value=mock_model):
        res_leaf_smut = pred_service.predict(normal_img_path)
        assert res_leaf_smut["predicted_index"] == 9
        assert res_leaf_smut["disease"] == "leaf_smut"
        assert res_leaf_smut["is_healthy"] is False
        assert res_leaf_smut["top3"][0]["disease"] == "leaf_smut"
        assert res_leaf_smut["top3"][0]["index"] == 9
        print("[PASS] (Mocked) Image prediction correctly handles leaf_smut (index 9, is_healthy=False).")
        
    # 3. Mocked unit test for normal (index 10)
    fake_logits_normal = torch.full((1, 13), -10.0)
    fake_logits_normal[0, 10] = 10.0 # normal
    mock_model.return_value = fake_logits_normal
    with patch("app.models.model_loader.ModelLoader.get_model", return_value=mock_model):
        res_mock_normal = pred_service.predict(normal_img_path)
        assert res_mock_normal["predicted_index"] == 10
        assert res_mock_normal["disease"] == "normal"
        assert res_mock_normal["is_healthy"] is True
        assert res_mock_normal["top3"][0]["disease"] == "normal"
        assert res_mock_normal["top3"][0]["index"] == 10
        print("[PASS] (Mocked) Image prediction correctly handles normal (index 10, is_healthy=True).")

def test_multimodal_missing_class_rejection_and_isolation():
    print("\n--- 3. Testing Multimodal Isolation From Missing Classes ---")
    mm_service = MultimodalPredictionService()
    test_img = Path("backend/test_images/normal/100111.jpg")
    
    # Run multimodal on normal image
    res_mm = mm_service.predict(test_img, field_id="FIELD_01")
    assert res_mm["predicted_class"] in config.MULTIMODAL_CLASSES
    assert res_mm["predicted_class"] not in ["leaf_smut", "normal"]
    assert len(res_mm["top_3_predictions"]) == 3
    for pred in res_mm["top_3_predictions"]:
        assert pred["disease"] in config.MULTIMODAL_CLASSES
        assert pred["disease"] not in ["leaf_smut", "normal"]
        # Verify index matches config.MULTIMODAL_CLASSES exactly
        assert pred["disease"] == config.MULTIMODAL_CLASSES[pred["index"]]
        # Index 9 MUST be sheath_blight, NOT leaf_smut!
        if pred["index"] == 9:
            assert pred["disease"] == "sheath_blight"
        # Index 10 MUST be tungro, NOT normal!
        if pred["index"] == 10:
            assert pred["disease"] == "tungro"
    print(f"Multimodal prediction on normal image + FIELD_01: {res_mm['predicted_class']} (conf: {res_mm['confidence']})")
    print("[PASS] Multimodal prediction strictly isolates 11-class mapping and never maps index 9 or 10 to leaf_smut/normal.")

def test_prediction_disagreement():
    print("\n--- 4. Testing Prediction Disagreement Behavior ---")
    pred_service = PredictionService()
    mm_service = MultimodalPredictionService()
    
    img_path = Path("backend/test_images/tungro/TUNGRO5_67.JPG")
    img_res = pred_service.predict(img_path)
    mm_res = mm_service.predict(img_path, field_id="FIELD_01")
    
    print(f"Image model prediction: {img_res['disease']} (index: {img_res['predicted_index']}, conf: {img_res['confidence']})")
    print(f"Multimodal model prediction: {mm_res['predicted_class']} (conf: {mm_res['confidence']})")
    
    assert img_res["disease"] == "tungro"
    assert img_res["predicted_index"] == 12 # in 13-class model
    assert mm_res["predicted_class"] == "sheath_blight" # in 11-class model
    
    # Verify both models retain their distinct labels and confidences
    assert img_res["disease"] != mm_res["predicted_class"]
    print("[PASS] Verified prediction disagreement between image model (tungro) and multimodal model (sheath_blight).")
    print("[PASS] Neither prediction overwrites the other; both endpoints report their own metrics independently.")

def test_gradcam_class_validation():
    print("\n--- 5. Testing Grad-CAM Class Validation ---")
    gradcam_service = GradCAMService()
    
    # Valid 13 classes
    for idx, name in enumerate(config.DISEASE_CLASSES):
        assert gradcam_service.validate_target_class(target_class=name) == idx
        assert gradcam_service.validate_target_class(target_index=idx) == idx
    print("[PASS] All 13 disease classes and indices (0-12) validated in Grad-CAM.")
    
    # leaf_smut and normal ARE valid in Grad-CAM
    assert gradcam_service.validate_target_class(target_class="leaf_smut") == 9
    assert gradcam_service.validate_target_class(target_class="normal") == 10
    print("[PASS] leaf_smut (9) and normal (10) are correctly validated in Grad-CAM.")
    
    # sheath_blight and tungro in Grad-CAM are index 11 and 12
    assert gradcam_service.validate_target_class(target_class="sheath_blight") == 11
    assert gradcam_service.validate_target_class(target_class="tungro") == 12
    print("[PASS] sheath_blight (11) and tungro (12) correctly validated in Grad-CAM.")
    
    # Invalid classes
    try:
        gradcam_service.validate_target_class(target_class="invalid_disease")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid target_class" in str(e)
        print(f"[PASS] Invalid class rejected by Grad-CAM: {e}")
        
    try:
        gradcam_service.validate_target_class(target_index=13)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid target_index" in str(e)
        print(f"[PASS] Out-of-bounds index (13) rejected by Grad-CAM: {e}")

def test_shap_class_validation():
    print("\n--- 6. Testing SHAP Class Validation ---")
    shap_service = SHAPService.get_instance()
    test_img = Path("backend/test_images/tungro/TUNGRO5_67.JPG")
    
    # 1. Valid multimodal classes (e.g. sheath_blight, tungro)
    res_sb = shap_service.explain_multimodal(test_img, field_id="FIELD_01", target_class="sheath_blight")
    assert res_sb["target_class"] == "sheath_blight"
    assert res_sb["target_index"] == 9 # In 11-class model
    print(f"[PASS] SHAP successfully explained sheath_blight (target_index: {res_sb['target_index']}).")
    
    res_tungro = shap_service.explain_multimodal(test_img, field_id="FIELD_01", target_class="tungro")
    assert res_tungro["target_class"] == "tungro"
    assert res_tungro["target_index"] == 10 # In 11-class model
    print(f"[PASS] SHAP successfully explained tungro (target_index: {res_tungro['target_index']}).")
    
    # 2. leaf_smut and normal MUST be rejected by SHAP!
    try:
        shap_service.explain_multimodal(test_img, field_id="FIELD_01", target_class="leaf_smut")
        assert False, "Should have rejected leaf_smut"
    except ValueError as e:
        assert "Invalid target_class 'leaf_smut'" in str(e)
        print(f"[PASS] SHAP safely rejected leaf_smut: {e}")
        
    try:
        shap_service.explain_multimodal(test_img, field_id="FIELD_01", target_class="normal")
        assert False, "Should have rejected normal"
    except ValueError as e:
        assert "Invalid target_class 'normal'" in str(e)
        print(f"[PASS] SHAP safely rejected normal: {e}")
        
    # 3. Out-of-bounds indices in SHAP (e.g. 11, 12, 13)
    try:
        shap_service.explain_multimodal(test_img, field_id="FIELD_01", target_index=11)
        assert False, "Should have rejected index 11"
    except ValueError as e:
        assert "Invalid target_index '11'" in str(e)
        print(f"[PASS] SHAP safely rejected target_index 11: {e}")
        
    # 4. Invalid disease name
    try:
        shap_service.explain_multimodal(test_img, field_id="FIELD_01", target_class="invalid_disease")
        assert False, "Should have rejected invalid_disease"
    except ValueError as e:
        assert "Invalid target_class 'invalid_disease'" in str(e)
        print(f"[PASS] SHAP safely rejected invalid class: {e}")

if __name__ == "__main__":
    print("================================================================================")
    print("STEP 11D.7 — CROSS-MODEL CLASS MAPPING AND PREDICTION CONSISTENCY AUDIT SUITE")
    print("================================================================================")
    test_class_mappings_against_training_artifacts()
    test_image_prediction_missing_classes()
    test_multimodal_missing_class_rejection_and_isolation()
    test_prediction_disagreement()
    test_gradcam_class_validation()
    test_shap_class_validation()
    print("\n================================================================================")
    print("ALL STEP 11D.7 CORE CHECKS PASSED SUCCESSFULLY!")
    print("================================================================================")
