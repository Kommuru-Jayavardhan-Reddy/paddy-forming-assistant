"""
Paddy Farming Assistant - STEP 11D.1 Field Mapping Verification Test Suite
Executes strict automated tests on field-to-satellite and image-to-field mappings.
"""

import sys
from pathlib import Path

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
from app import config
from app.services.field_mapping import FieldMappingService


def run_tests():
    print("=" * 70)
    print("STEP 11D.1 — FIELD MAPPING VERIFICATION TEST SUITE")
    print("=" * 70)

    # 1. Configuration & Path Verification
    print("\n[Test 1] Verifying Artifact Paths Configuration...")
    paths_to_check = {
        "SATELLITE_SEQUENCES_PATH": config.SATELLITE_SEQUENCES_PATH,
        "FIELD_MASTER_MAPPING_PATH": config.FIELD_MASTER_MAPPING_PATH,
        "FIELD_LOCATIONS_PATH": config.FIELD_LOCATIONS_PATH,
        "MULTIMODAL_DATASET_MAPPING_PATH": config.MULTIMODAL_DATASET_MAPPING_PATH,
        "FIELD_EMBEDDINGS_PATH": config.FIELD_EMBEDDINGS_PATH,
        "PAIRED_SATELLITE_EMBEDDINGS_PATH": config.PAIRED_SATELLITE_EMBEDDINGS_PATH,
    }
    for name, path in paths_to_check.items():
        assert path.exists(), f"Missing required file: {name} at {path}"
        print(f"  [OK] {name}: FOUND ({path.name})")

    # 2. Service Loading
    print("\n[Test 2] Loading FieldMappingService...")
    service = FieldMappingService.get_instance()
    assert service.is_loaded, f"Service failed to load: {service._load_errors}"
    print("  [OK] FieldMappingService initialized and loaded cleanly.")

    # 3. Validation Suite Execution
    print("\n[Test 3] Running Full Validation Suite...")
    report = service.validate_mappings()
    print(f"  Validation Status: {report['status']}")
    for k, v in report["checks"].items():
        print(f"    - {k}: {v.get('passed', True)}")
    assert report["status"] == "PASS", f"Validation failed with errors: {report['errors']}"

    # 4. Satellite Tensor Properties
    print("\n[Test 4] Verifying Satellite Data Tensor Properties...")
    seq_arr = np.load(config.SATELLITE_SEQUENCES_PATH)
    assert seq_arr.shape == (58, 10, 3), f"Unexpected sequence shape: {seq_arr.shape}"
    assert seq_arr.dtype == np.float32, f"Unexpected sequence dtype: {seq_arr.dtype}"
    assert not np.isnan(seq_arr).any(), "NaN found in satellite sequence tensor"
    assert not np.isinf(seq_arr).any(), "Inf found in satellite sequence tensor"
    print(f"  [OK] Shape: {seq_arr.shape} (58 fields, 10 timesteps, 3 features)")
    print(f"  [OK] Dtype: {seq_arr.dtype}")
    print(f"  [OK] Features: {config.SATELLITE_FEATURES}")
    print(f"  [OK] Value range: [{np.min(seq_arr):.4f}, {np.max(seq_arr):.4f}]")

    # 5. Field Catalog Integrity
    print("\n[Test 5] Verifying 58 Master Satellite Fields (0-Indexed)...")
    fields = service.list_fields()
    assert len(fields) == 58, f"Expected 58 fields, got {len(fields)}"
    for i, f_info in enumerate(fields):
        expected_fid = f"FIELD_{i+1:02d}"
        assert f_info["field_id"] == expected_fid, f"Field ID mismatch at {i}: {f_info['field_id']} vs {expected_fid}"
        assert f_info["sequence_index"] == i, f"Sequence index mismatch at {i}: {f_info['sequence_index']} != {i}"
        assert f_info["embedding_index"] == i, f"Embedding index mismatch at {i}: {f_info['embedding_index']} != {i}"
    print("  [OK] All 58 fields indexed strictly from 0 to 57 without gaps or off-by-one errors.")

    # 6. Field Lookup Functionality
    print("\n[Test 6] Testing Field Lookup and Sequence Retrieval...")
    f01 = service.get_field("FIELD_01")
    assert f01 is not None, "FIELD_01 lookup failed"
    assert f01["sequence_shape"] == (10, 3), f"FIELD_01 sequence shape: {f01['sequence_shape']}"
    assert "sequence" in f01 and isinstance(f01["sequence"], np.ndarray)
    assert np.allclose(f01["sequence"], seq_arr[0]), "FIELD_01 sequence does not match seq_arr[0]"
    print("  [OK] FIELD_01 sequence matches seq_arr[0] with 0 error.")

    f58 = service.get_field("FIELD_58")
    assert f58 is not None, "FIELD_58 lookup failed"
    assert np.allclose(f58["sequence"], seq_arr[57]), "FIELD_58 sequence does not match seq_arr[57]"
    print("  [OK] FIELD_58 sequence matches seq_arr[57] with 0 error.")

    # 7. Image-to-Field Mapping Lookup
    print("\n[Test 7] Testing Image Lookup across classes...")
    test_samples = [
        ("Image1 2026-09-07 at 7.18.55 AM.jpeg", "FIELD_01", 0, "bacterial_leaf_blight"),
        ("WhatsApp Image 2026-09-07 at 5.50.48 PM.png", "FIELD_02", 1, "bacterial_leaf_streak"),
        ("6197266757773366206.jpg", "FIELD_03", 2, "sheath_blight"),
        ("6206460066550978060.jpg", "FIELD_54", 53, "tungro"),
    ]
    for img_name, exp_field, exp_idx, exp_label in test_samples:
        mapping = service.get_image_mapping(img_name)
        assert mapping is not None, f"Mapping failed for {img_name}"
        assert mapping["nearest_satellite_field"] == exp_field, f"Field mismatch for {img_name}: {mapping['nearest_satellite_field']} != {exp_field}"
        assert mapping["satellite_embedding_index"] == exp_idx, f"Index mismatch for {img_name}: {mapping['satellite_embedding_index']} != {exp_idx}"
        assert mapping["disease_label"] == exp_label, f"Label mismatch for {img_name}: {mapping['disease_label']} != {exp_label}"
        assert "sequence" in mapping and mapping["sequence"].shape == (10, 3)
        print(f"  [OK] {img_name[:35]:35s} -> {exp_field} (idx={exp_idx}) -> {exp_label:24s} [PASS]")

    # 8. Embedding Paired Consistency Check
    print("\n[Test 8] Checking Paired Embeddings Matrix Identity...")
    paired_arr = np.load(config.PAIRED_SATELLITE_EMBEDDINGS_PATH)
    emb_arr = np.load(config.FIELD_EMBEDDINGS_PATH)
    assert paired_arr.shape == (640, 256), f"Unexpected paired shape: {paired_arr.shape}"
    assert emb_arr.shape == (58, 256), f"Unexpected field embedding shape: {emb_arr.shape}"

    # Verify first row
    first_img_mapping = service.get_image_mapping("Image1 2026-09-07 at 7.18.55 AM.jpeg")
    first_sat_idx = first_img_mapping["satellite_embedding_index"]
    assert np.allclose(paired_arr[0], emb_arr[first_sat_idx]), "Paired embedding row 0 does not match field embedding"
    print("  [OK] Paired embedding tensor (640, 256) exactly aligns with field embeddings (58, 256).")

    # 9. Verify Non-existent Lookups Gracefully Return None
    print("\n[Test 9] Edge Cases & Negative Lookups...")
    assert service.get_field("NON_EXISTENT_FIELD") is None
    assert service.get_image_mapping("non_existent_image.jpg") is None
    assert service.get_satellite_sequence("NON_EXISTENT_FIELD") is None
    print("  [OK] Non-existent fields and images safely return None.")

    print("\n" + "=" * 70)
    print("ALL STEP 11D.1 CHECKS PASSED SUCCESSFULLY (PASS)")
    print("=" * 70)
    return True



if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)
