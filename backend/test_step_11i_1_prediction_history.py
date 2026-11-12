"""
Paddy Farming Assistant - STEP 11I.1 Prediction History Storage & Retrieval Verification Test Suite
===================================================================================================
Tests disease detection prediction storage, repository validation, rollback handling,
retrieval APIs, pagination, filters, and backward compatibility.

Guarantees 100% database non-pollution: all tests use isolated transactions with rollback
or strictly clean up any live test inferences to preserve the pristine baseline (35 records).
"""

import asyncio
import io
import json
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any

import requests
from PIL import Image
from sqlalchemy import text, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.db.session import AsyncSessionLocal
from app.db.models.prediction import PredictionHistory
from app.db.models.field import Field
from app.db.repositories.prediction_repository import PredictionRepository

logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"
TEST_IMAGE_PATH = Path("test_images/normal/100111.jpg")

EXPECTED_BASELINE_COUNTS = {
    "buyers": 17,
    "market_prices": 100,
    "fields": 58,
    "satellite_observations": 580,
    "prediction_history": 35,
    "weather_records": 92,
    "reports": 0,
}


@contextmanager
def assert_raises(exc_type, match=None):
    """Context manager for asserting expected exceptions and messages."""
    try:
        yield
    except exc_type as exc:
        if match and match not in str(exc):
            raise AssertionError(f"Expected error message containing '{match}', got: '{exc}'")
        return
    raise AssertionError(f"Expected exception {exc_type.__name__} was not raised.")


async def get_db_counts() -> Dict[str, int]:
    """Queries and returns current row counts across all major tables."""
    session = AsyncSessionLocal()
    try:
        counts = {}
        for tbl in EXPECTED_BASELINE_COUNTS.keys():
            res = await session.execute(text(f"SELECT count(*) FROM {tbl}"))
            counts[tbl] = res.scalar() or 0
        return counts
    finally:
        await session.close()


class Step11I1TestSuite:
    """Comprehensive test suite for STEP 11I.1."""

    async def test_01_database_baseline_integrity(self):
        """Verify initial database table row counts match expected baseline."""
        counts = await get_db_counts()
        print("\n[Test 01] Verifying Pre-Test Database Baseline Counts...")
        for tbl, expected in EXPECTED_BASELINE_COUNTS.items():
            actual = counts[tbl]
            print(f"  Table '{tbl}': actual={actual}, expected={expected}")
            assert actual == expected, f"Table '{tbl}' count mismatch: {actual} != {expected}"
        print("  [PASS] Baseline database counts verified.")

    async def test_02_prediction_repository_validation_constraints(self):
        """Verify input validation rules in PredictionRepository before database submission."""
        print("\n[Test 02] Testing PredictionRepository Validation Rules...")
        session = AsyncSessionLocal()
        try:
            repo = PredictionRepository(session)

            # 1. Invalid prediction mode
            with assert_raises(ValueError, match="Invalid prediction_mode"):
                repo.validate_prediction_inputs("spectral_only", 0, 0.95)

            # 2. Confidence out of bounds
            with assert_raises(ValueError, match="outside valid"):
                repo.validate_prediction_inputs("image_only", 0, 1.05)
            with assert_raises(ValueError, match="outside valid"):
                repo.validate_prediction_inputs("image_only", 0, -0.01)

            # 3. Image-only class index out of bounds [0, 12]
            with assert_raises(ValueError, match="outside valid"):
                repo.validate_prediction_inputs("image_only", 13, 0.95)
            with assert_raises(ValueError, match="outside valid"):
                repo.validate_prediction_inputs("image_only", -1, 0.95)

            # 4. Multimodal class index out of bounds [0, 10]
            with assert_raises(ValueError, match="outside valid"):
                repo.validate_prediction_inputs("multimodal", 11, 0.95)
            with assert_raises(ValueError, match="outside valid"):
                repo.validate_prediction_inputs("multimodal", -1, 0.95)

            # 5. Valid boundaries
            repo.validate_prediction_inputs("image_only", 0, 0.0)
            repo.validate_prediction_inputs("image_only", 12, 1.0)
            repo.validate_prediction_inputs("multimodal", 0, 0.5)
            repo.validate_prediction_inputs("multimodal", 10, 0.85)

            print("  [PASS] All repository constraint checks verified successfully.")
        finally:
            await session.close()

    async def test_03_prediction_persistence_isolated_transaction(self):
        """Test persistence of image_only and multimodal predictions in an isolated rolled-back transaction."""
        print("\n[Test 03] Testing Prediction Persistence in Isolated Transaction...")
        session = AsyncSessionLocal()
        try:
            repo = PredictionRepository(session)

            # Fetch a real field for association
            field_res = await session.execute(select(Field).limit(1))
            sample_field = field_res.scalar_one_or_none()
            field_uuid = sample_field.id if sample_field else None

            # 1. Create image_only record
            test_sha256 = "a" * 64
            img_rec = await repo.create_prediction(
                prediction_mode="image_only",
                model_name="EfficientNet-B4",
                model_version="test_eval_v1",
                predicted_disease="tungro",
                predicted_class_index=12,
                confidence=0.9654,
                is_healthy=False,
                top_k_predictions=[
                    {"disease": "tungro", "probability": 0.9654, "index": 12},
                    {"disease": "bacterial_leaf_blight", "probability": 0.0210, "index": 1},
                ],
                field_id=field_uuid,
                low_confidence=False,
                image_sha256=test_sha256,
                farmer_question="What is this discoloration?",
                response_language="en",
                inference_latency_ms=115.42,
                device="cpu",
            )
            assert img_rec.id is not None
            assert img_rec.predicted_disease == "tungro"
            assert float(img_rec.confidence) == 0.9654
            assert img_rec.image_sha256 == test_sha256
            assert img_rec.created_at is not None

            # 2. Query back by ID
            fetched_img = await repo.get_by_id(img_rec.id)
            assert fetched_img is not None
            assert fetched_img.prediction_mode == "image_only"
            assert fetched_img.predicted_class_index == 12

            # 3. Create multimodal record
            mm_rec = await repo.create_prediction(
                prediction_mode="multimodal",
                model_name="TemporalCrossAttention",
                model_version="test_mm_v1",
                predicted_disease="sheath_blight",
                predicted_class_index=8,
                confidence=0.8912,
                is_healthy=False,
                top_k_predictions=[
                    {"disease": "sheath_blight", "probability": 0.8912, "index": 8},
                ],
                field_id=field_uuid,
                attention_weights=[0.1] * 10,
                image_sha256="b" * 64,
                response_language="en",
                inference_latency_ms=180.25,
                device="cpu",
            )
            assert mm_rec.id is not None
            assert mm_rec.prediction_mode == "multimodal"
            assert len(mm_rec.attention_weights) == 10

            fetched_mm = await repo.get_by_id(mm_rec.id)
            assert fetched_mm is not None
            assert fetched_mm.predicted_disease == "sheath_blight"

            # 4. Rollback transaction to ensure zero DB pollution
            await session.rollback()
            print("  [PASS] Persistence verified; transaction rolled back cleanly.")

            # 5. Confirm records do not exist after rollback
            check_img = await repo.get_by_id(img_rec.id)
            check_mm = await repo.get_by_id(mm_rec.id)
            assert check_img is None, "img_rec persisted despite rollback!"
            assert check_mm is None, "mm_rec persisted despite rollback!"
            print("  [PASS] Verified 0 synthetic records remained post-rollback.")

        finally:
            await session.close()

    async def test_04_database_persistence_failure_rollback(self):
        """Test that errors trigger database rollback and do not corrupt the session or table."""
        print("\n[Test 04] Testing Database Failure Rollback Handling...")
        session = AsyncSessionLocal()
        try:
            repo = PredictionRepository(session)

            # Intentionally attempt to insert record with non-existent foreign key (violates FK constraint)
            fake_field_id = uuid.uuid4()
            with assert_raises(Exception):
                await repo.create_prediction(
                    prediction_mode="image_only",
                    model_name="EfficientNet-B4",
                    model_version="v1",
                    predicted_disease="tungro",
                    predicted_class_index=12,
                    confidence=0.95,
                    is_healthy=False,
                    top_k_predictions=[],
                    field_id=fake_field_id,  # Invalid FK
                )
                await session.flush()

            # Rollback cleanly
            await session.rollback()
            print("  [PASS] FK violation caught and rolled back without state corruption.")

            # Verify session is still completely usable
            fresh_count = await repo.count()
            assert fresh_count == 35
            print(f"  [PASS] Session restored cleanly; prediction_history count={fresh_count}.")
        finally:
            await session.close()

    async def test_05_live_prediction_history_retrieval_and_pagination(self):
        """Test GET /predictions live endpoint for correct retrieval, pagination, and count."""
        print("\n[Test 05] Testing Live Prediction History Retrieval & Pagination...")
        # 1. Default retrieval
        resp = requests.get(f"{BASE_URL}/predictions", timeout=10)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["total_predictions"] == 35
        assert len(data["predictions"]) == 35

        # 2. Paginated page 1 (page_size=10)
        resp_p1 = requests.get(f"{BASE_URL}/predictions?page=1&page_size=10", timeout=10)
        assert resp_p1.status_code == 200
        d1 = resp_p1.json()
        assert d1["total_predictions"] == 35
        assert len(d1["predictions"]) == 10
        p1_ids = [p["id"] for p in d1["predictions"]]

        # 3. Paginated page 2 (page_size=10)
        resp_p2 = requests.get(f"{BASE_URL}/predictions?page=2&page_size=10", timeout=10)
        assert resp_p2.status_code == 200
        d2 = resp_p2.json()
        assert len(d2["predictions"]) == 10
        p2_ids = [p["id"] for p in d2["predictions"]]

        # Ensure pages do not overlap
        overlap = set(p1_ids).intersection(set(p2_ids))
        assert len(overlap) == 0, f"Pages overlap with IDs: {overlap}"

        # 4. Paginated page 4 (remainder page, 35 - 30 = 5 items)
        resp_p4 = requests.get(f"{BASE_URL}/predictions?page=4&page_size=10", timeout=10)
        assert resp_p4.status_code == 200
        d4 = resp_p4.json()
        assert len(d4["predictions"]) == 5

        print("  [PASS] Pagination (pages 1, 2, 4) and distinct offset verified.")

    async def test_06_live_prediction_history_filters(self):
        """Test GET /predictions with mode, disease, field_id, date range, and prediction_id filters."""
        print("\n[Test 06] Testing Live Prediction History Filtering...")
        # 1. Filter by prediction_mode: image_only (25 expected)
        r_img = requests.get(f"{BASE_URL}/predictions?prediction_mode=image_only", timeout=10)
        assert r_img.status_code == 200
        d_img = r_img.json()
        assert d_img["total_predictions"] == 25
        for p in d_img["predictions"]:
            assert p["prediction_mode"] == "image_only"

        # 2. Filter by prediction_mode: multimodal (10 expected)
        r_mm = requests.get(f"{BASE_URL}/predictions?prediction_mode=multimodal", timeout=10)
        assert r_mm.status_code == 200
        d_mm = r_mm.json()
        assert d_mm["total_predictions"] == 10
        for p in d_mm["predictions"]:
            assert p["prediction_mode"] == "multimodal"

        # 3. Filter by disease: tungro (22 expected)
        r_dis = requests.get(f"{BASE_URL}/predictions?disease=tungro", timeout=10)
        assert r_dis.status_code == 200
        d_dis = r_dis.json()
        assert d_dis["total_predictions"] == 22
        for p in d_dis["predictions"]:
            assert p["predicted_disease"].lower() == "tungro"

        # Case-insensitive disease filter
        r_dis_ci = requests.get(f"{BASE_URL}/predictions?disease=TUNGRO", timeout=10)
        assert r_dis_ci.status_code == 200
        assert r_dis_ci.json()["total_predictions"] == 22

        # Disease: sheath_blight (10 expected)
        r_sb = requests.get(f"{BASE_URL}/predictions?disease=sheath_blight", timeout=10)
        assert r_sb.status_code == 200
        assert r_sb.json()["total_predictions"] == 10

        # Disease: normal (3 expected)
        r_norm = requests.get(f"{BASE_URL}/predictions?disease=normal", timeout=10)
        assert r_norm.status_code == 200
        assert r_norm.json()["total_predictions"] == 3

        # 4. Filter by field_id: FIELD_01 (20 expected)
        r_f01 = requests.get(f"{BASE_URL}/predictions?field_id=FIELD_01", timeout=10)
        assert r_f01.status_code == 200
        d_f01 = r_f01.json()
        assert d_f01["total_predictions"] == 20

        # Filter by non-existent field_id
        r_fnil = requests.get(f"{BASE_URL}/predictions?field_id=NON_EXISTENT_FIELD_999", timeout=10)
        assert r_fnil.status_code == 200
        assert r_fnil.json()["total_predictions"] == 0

        # 5. Date range filters
        # Match all (created on 2026-10-14)
        r_date_match = requests.get(
            f"{BASE_URL}/predictions?start_date=2026-10-14T00:00:00Z&end_date=2026-10-15T00:00:00Z",
            timeout=10,
        )
        assert r_date_match.status_code == 200
        assert r_date_match.json()["total_predictions"] == 35

        # Historical non-matching date range
        r_date_empty = requests.get(
            f"{BASE_URL}/predictions?start_date=2023-01-01T00:00:00Z&end_date=2023-12-31T23:59:59Z",
            timeout=10,
        )
        assert r_date_empty.status_code == 200
        assert r_date_empty.json()["total_predictions"] == 0

        # 6. Specific prediction_id query filter
        sample_pred = d_img["predictions"][0]
        target_id = sample_pred["id"]
        r_pid = requests.get(f"{BASE_URL}/predictions?prediction_id={target_id}", timeout=10)
        assert r_pid.status_code == 200
        d_pid = r_pid.json()
        assert d_pid["total_predictions"] == 1
        assert d_pid["predictions"][0]["id"] == target_id

        print("  [PASS] All filters (mode, disease, field, date range, prediction_id) passed.")

    async def test_07_live_prediction_by_id_endpoint(self):
        """Test GET /predictions/{prediction_id} for valid record, privacy protection, and 404/422 handling."""
        print("\n[Test 07] Testing GET /predictions/{prediction_id} Endpoint...")
        # 1. Fetch valid ID
        list_res = requests.get(f"{BASE_URL}/predictions?page_size=1", timeout=10)
        assert list_res.status_code == 200
        sample_id = list_res.json()["predictions"][0]["id"]

        r_single = requests.get(f"{BASE_URL}/predictions/{sample_id}", timeout=10)
        assert r_single.status_code == 200
        item = r_single.json()
        assert item["id"] == sample_id
        assert "predicted_disease" in item
        assert "confidence" in item
        assert "created_at" in item
        assert "image_sha256" in item

        # PRIVACY/SECURITY: Ensure raw storage paths and image contents are NEVER exposed
        assert "image_storage_path" not in item
        assert "gradcam_storage_path" not in item
        assert "image_bytes" not in item
        assert "raw_content" not in item

        # 2. Non-existent UUID -> 404
        r_404 = requests.get(f"{BASE_URL}/predictions/00000000-0000-0000-0000-000000000000", timeout=10)
        assert r_404.status_code == 404
        assert "was not found" in r_404.json()["detail"]

        # 3. Invalid UUID syntax -> 422
        r_422 = requests.get(f"{BASE_URL}/predictions/invalid-uuid-format", timeout=10)
        assert r_422.status_code == 422

        print("  [PASS] Single prediction retrieval, security masking, 404, and 422 verified.")

    async def test_08_live_filter_validation_and_error_handling(self):
        """Test invalid query filter validation on GET /predictions."""
        print("\n[Test 08] Testing Invalid Query Filter Handling...")
        # 1. Invalid prediction_mode
        r_inv_mode = requests.get(f"{BASE_URL}/predictions?prediction_mode=ultrasound", timeout=10)
        assert r_inv_mode.status_code == 400
        assert "Invalid prediction_mode 'ultrasound'" in r_inv_mode.json()["detail"]

        # 2. Inverted date range (start_date > end_date)
        r_inv_date = requests.get(
            f"{BASE_URL}/predictions?start_date=2026-12-01T00:00:00Z&end_date=2026-01-01T00:00:00Z",
            timeout=10,
        )
        assert r_inv_date.status_code == 400
        assert "Invalid date range" in r_inv_date.json()["detail"]

        # 3. Malformed prediction_id query parameter
        r_inv_pid = requests.get(f"{BASE_URL}/predictions?prediction_id=not-a-valid-uuid", timeout=10)
        assert r_inv_pid.status_code == 400
        assert "must be a valid UUID" in r_inv_pid.json()["detail"]

        print("  [PASS] Clean 400 Bad Request handling verified for all invalid filters.")

    async def test_09_live_prediction_endpoint_backward_compatibility_and_persistence(self):
        """Test POST /predict generates prediction, persists record to DB, and is cleanly cleaned up."""
        print("\n[Test 09] Testing Live POST /predict Persistence and Backward Compatibility...")
        assert TEST_IMAGE_PATH.exists(), f"Test image missing: {TEST_IMAGE_PATH}"

        with open(TEST_IMAGE_PATH, "rb") as f:
            img_bytes = f.read()

        created_pred_id = None
        try:
            # Execute real inference request
            files = {"file": ("test_leaf.jpg", img_bytes, "image/jpeg")}
            data = {"field_id": "FIELD_01", "question": "Are these spots normal?"}
            resp = requests.post(f"{BASE_URL}/predict", files=files, data=data, timeout=20)

            assert resp.status_code == 200, f"Inference failed with {resp.status_code}: {resp.text}"
            res_data = resp.json()

            # Verify response schema backward compatibility
            assert "disease" in res_data
            assert "confidence" in res_data
            assert "predicted_index" in res_data
            assert "top3" in res_data or "top_3_predictions" in res_data
            assert "field_id" in res_data
            assert "prediction_id" in res_data, "Response missing persisted prediction_id!"

            created_pred_id = res_data["prediction_id"]
            print(f"  [PASS] Inference succeeded: disease='{res_data['disease']}', prediction_id={created_pred_id}")

            # Verify immediate retrieval via GET /predictions/{id}
            r_verify = requests.get(f"{BASE_URL}/predictions/{created_pred_id}", timeout=10)
            assert r_verify.status_code == 200
            persisted_rec = r_verify.json()
            assert persisted_rec["predicted_disease"] == res_data["disease"]
            assert abs(persisted_rec["confidence"] - float(res_data["confidence"])) < 0.001
            assert persisted_rec["prediction_mode"] == "image_only"
            assert len(persisted_rec["top_k_predictions"]) > 0, "Top-K predictions not persisted!"
            print(f"  [PASS] Verified persisted record in PostgreSQL with matching confidence & disease.")
        finally:
            # Clean up this single test inference immediately to maintain strictly 35 records
            if created_pred_id:
                session = AsyncSessionLocal()
                try:
                    pred_uuid = uuid.UUID(created_pred_id)
                    del_stmt = delete(PredictionHistory).where(PredictionHistory.id == pred_uuid)
                    await session.execute(del_stmt)
                    await session.commit()
                    print(f"  [PASS] Test prediction record {created_pred_id} cleaned up safely.")
                finally:
                    await session.close()

    async def test_10_post_test_database_integrity(self):
        """Confirm database row counts across all tables are completely preserved at baseline."""
        print("\n[Test 10] Verifying Post-Test Database Baseline Integrity...")
        counts = await get_db_counts()
        for tbl, expected in EXPECTED_BASELINE_COUNTS.items():
            actual = counts[tbl]
            print(f"  Table '{tbl}': actual={actual}, expected={expected}")
            assert actual == expected, f"Table '{tbl}' count corrupted: {actual} != {expected}"
        print("  [PASS] All 7 database tables remain completely pristine with zero synthetic pollution.")


async def main():
    print("=" * 80)
    print("STEP 11I.1 — PREDICTION HISTORY STORAGE AUDIT & VERIFICATION TEST SUITE")
    print("=" * 80)

    suite = Step11I1TestSuite()
    tests = [
        suite.test_01_database_baseline_integrity,
        suite.test_02_prediction_repository_validation_constraints,
        suite.test_03_prediction_persistence_isolated_transaction,
        suite.test_04_database_persistence_failure_rollback,
        suite.test_05_live_prediction_history_retrieval_and_pagination,
        suite.test_06_live_prediction_history_filters,
        suite.test_07_live_prediction_by_id_endpoint,
        suite.test_08_live_filter_validation_and_error_handling,
        suite.test_09_live_prediction_endpoint_backward_compatibility_and_persistence,
        suite.test_10_post_test_database_integrity,
    ]

    passed = 0
    failed = 0

    for test in tests:
        name = test.__name__
        try:
            await test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[FAIL] {name} failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"TEST EXECUTION SUMMARY: {passed} PASSED, {failed} FAILED (TOTAL {len(tests)})")
    print("=" * 80)

    if failed > 0:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
