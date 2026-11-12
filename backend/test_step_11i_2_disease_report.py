"""
Paddy Farming Assistant - STEP 11I.2 Disease Detection Report Generation Test Suite
===================================================================================
Tests diagnostic report compilation from real stored predictions, metadata persistence,
duplicate handling/idempotency, privacy protection, retrieval APIs, pagination,
filtering, error handling, database rollback, and zero-pollution table cleanup.
"""

import asyncio
import json
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import requests
from sqlalchemy import text, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.db.models.prediction import PredictionHistory
from app.db.models.report import Report
from app.db.models.field import Field
from app.db.repositories.other_repositories import ReportRepository
from app.services.report_service import ReportService, DISCLAIMER_TEXT

logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"

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
    """Context manager for asserting expected exceptions and error messages."""
    try:
        yield
    except exc_type as exc:
        if match and match not in str(exc):
            raise AssertionError(f"Expected error message containing '{match}', got: '{exc}'")
        return
    raise AssertionError(f"Expected exception {exc_type.__name__} was not raised.")


async def get_db_counts() -> Dict[str, int]:
    """Queries and returns current row counts across all major database tables."""
    session = AsyncSessionLocal()
    try:
        counts = {}
        for tbl in EXPECTED_BASELINE_COUNTS.keys():
            res = await session.execute(text(f"SELECT count(*) FROM {tbl}"))
            counts[tbl] = res.scalar() or 0
        return counts
    finally:
        await session.close()


class Step11I2TestSuite:
    """Comprehensive test suite for STEP 11I.2."""

    def __init__(self):
        self.created_report_ids: List[str] = []

    async def test_01_database_baseline_integrity(self):
        """Verify pre-test database table row counts match expected baseline."""
        print("\n[Test 01] Verifying Pre-Test Database Baseline Counts...")
        counts = await get_db_counts()
        for tbl, expected in EXPECTED_BASELINE_COUNTS.items():
            actual = counts[tbl]
            print(f"  Table '{tbl}': actual={actual}, expected={expected}")
            assert actual == expected, f"Table '{tbl}' count mismatch: {actual} != {expected}"
        print("  [PASS] Baseline database counts verified.")

    async def test_02_report_repository_validation_and_methods(self):
        """Verify ReportRepository input constraints and CRUD methods in an isolated rolled-back transaction."""
        print("\n[Test 02] Testing ReportRepository Validation & Methods in Isolated Transaction...")
        session = AsyncSessionLocal()
        try:
            repo = ReportRepository(session)

            # 1. Constraint validation
            with assert_raises(ValueError, match="Invalid report_type"):
                await repo.create_report(report_type="weather_forecast", title="Invalid Type")

            with assert_raises(ValueError, match="Invalid status"):
                await repo.create_report(
                    report_type="disease_diagnostic",
                    title="Invalid Status",
                    status="in_progress",
                )

            # 2. Create in isolated transaction
            rep = await repo.create_report(
                report_type="disease_diagnostic",
                title="Test Isolated Diagnostic Report",
                summary="Isolated transaction test summary",
                status="completed",
                file_path="reports/diagnostic/test_isolated.json",
                file_format="json",
                file_size_bytes=1024,
                report_metadata={"test_key": "test_val"},
                generated_by="test_suite",
            )
            assert rep.id is not None
            assert rep.report_type == "disease_diagnostic"
            assert rep.status == "completed"

            # 3. Retrieve by ID
            fetched = await repo.get_by_id(rep.id)
            assert fetched is not None
            assert fetched.title == "Test Isolated Diagnostic Report"

            # 4. Rollback transaction to ensure zero DB pollution
            await session.rollback()
            print("  [PASS] Created and verified report in session; transaction rolled back cleanly.")

            # 5. Confirm report was not persisted to disk
            check = await repo.get_by_id(rep.id)
            assert check is None, "Report persisted despite transaction rollback!"
            print("  [PASS] Verified 0 synthetic records remained post-rollback.")
        finally:
            await session.close()

    async def test_03_generate_report_from_real_image_only_prediction(self):
        """Test report generation from a real stored image_only prediction."""
        print("\n[Test 03] Testing Report Generation from Real Image-Only Prediction...")
        # Fetch one real image_only prediction
        r_pred = requests.get(f"{BASE_URL}/predictions?prediction_mode=image_only&page_size=1", timeout=10)
        assert r_pred.status_code == 200
        pred_item = r_pred.json()["predictions"][0]
        pred_id = pred_item["id"]

        # Call POST /reports/generate/{prediction_id}
        resp = requests.post(f"{BASE_URL}/reports/generate/{pred_id}", timeout=10)
        assert resp.status_code == 201, f"Expected 201 Created, got {resp.status_code}: {resp.text}"
        data = resp.json()

        self.created_report_ids.append(data["id"])
        print(f"  Generated Report ID: {data['id']}")
        print(f"  Title: {data['title']}")

        # Verify core fields
        assert data["prediction_id"] == pred_id
        assert data["report_type"] == "disease_diagnostic"
        assert data["status"] == "completed"
        assert data["file_format"] == "json"
        assert data["file_size_bytes"] > 0
        assert pred_item["predicted_disease"].replace("_", " ").title() in data["title"]

        # Verify metadata
        meta = data["report_metadata"]
        assert meta["prediction_id"] == pred_id
        assert meta["predicted_disease"] == pred_item["predicted_disease"]
        assert abs(meta["confidence"] - pred_item["confidence"]) < 0.001
        assert meta["prediction_mode"] == "image_only"
        assert meta["model_name"] == pred_item["model_name"]
        assert meta["model_version"] == pred_item["model_version"]
        assert meta["predicted_class_index"] == pred_item["predicted_class_index"]
        assert meta["image_sha256"] == pred_item["image_sha256"]
        assert meta["prediction_timestamp"] is not None
        assert meta["report_generated_at"] is not None
        assert "disclaimer" in meta
        assert "DISCLAIMER" in meta["disclaimer"]
        assert "decision support" in meta["disclaimer"]

        print("  [PASS] Image-only report compiled and verified successfully.")

    async def test_04_generate_report_from_real_multimodal_prediction(self):
        """Test report generation from a real stored multimodal prediction with temporal attention."""
        print("\n[Test 04] Testing Report Generation from Real Multimodal Prediction...")
        # Fetch one real multimodal prediction
        r_pred = requests.get(f"{BASE_URL}/predictions?prediction_mode=multimodal&page_size=1", timeout=10)
        assert r_pred.status_code == 200
        pred_item = r_pred.json()["predictions"][0]
        pred_id = pred_item["id"]

        resp = requests.post(f"{BASE_URL}/reports/generate/{pred_id}", timeout=10)
        assert resp.status_code == 201, f"Expected 201 Created, got {resp.status_code}: {resp.text}"
        data = resp.json()

        self.created_report_ids.append(data["id"])
        print(f"  Generated Report ID: {data['id']}")

        assert data["prediction_id"] == pred_id
        meta = data["report_metadata"]
        assert meta["prediction_mode"] == "multimodal"
        assert meta["model_name"] == "TemporalCrossAttention"
        assert meta["attention_weights"] is not None
        assert len(meta["attention_weights"]) == 10

        # If field is associated, verify safe external field identification
        if pred_item.get("field_id"):
            assert meta["field_id"] == pred_item["field_id"]
            assert meta["field_external_id"] is not None
            print(f"  Linked Field: external_id={meta['field_external_id']}, name={meta['field_name']}")

        print("  [PASS] Multimodal report compiled with 10-step attention and field metadata.")

    async def test_05_privacy_and_security_leak_check(self):
        """Verify report responses strictly conceal raw GPS coordinates and private server paths."""
        print("\n[Test 05] Verifying Privacy & Security Masking (No GPS / Server Path Leaks)...")
        assert len(self.created_report_ids) > 0
        rep_id = self.created_report_ids[0]

        resp = requests.get(f"{BASE_URL}/reports/{rep_id}", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        raw_text = resp.text

        # 1. No server filesystem paths exposed in response
        assert "file_path" not in data, "file_path exposed in public ReportResponse!"
        assert "image_storage_path" not in raw_text, "image_storage_path leaked in response!"
        assert "gradcam_storage_path" not in raw_text, "gradcam_storage_path leaked in response!"
        assert "C:\\" not in raw_text, "Absolute Windows path leaked!"
        assert "/home/" not in raw_text, "Absolute Linux path leaked!"

        # 2. No raw GPS coordinates exposed in report response
        assert "latitude" not in raw_text.lower(), "Raw latitude leaked in report response!"
        assert "longitude" not in raw_text.lower(), "Raw longitude leaked in report response!"

        print("  [PASS] Complete privacy and security masking verified (0 coordinates / paths leaked).")

    async def test_06_duplicate_request_idempotency_and_force_regenerate(self):
        """Test duplicate report requests return existing report (200), and force_regenerate creates new report (201)."""
        print("\n[Test 06] Testing Duplicate Request Idempotency & Force Regenerate...")
        r_pred = requests.get(f"{BASE_URL}/predictions?page_size=1", timeout=10)
        pred_id = r_pred.json()["predictions"][0]["id"]

        # Call 1: should return existing report (created in earlier test)
        r_dup = requests.post(f"{BASE_URL}/reports/generate/{pred_id}", timeout=10)
        assert r_dup.status_code == 200, f"Expected 200 OK on duplicate, got {r_dup.status_code}"
        d_dup = r_dup.json()
        assert d_dup["id"] in self.created_report_ids
        print(f"  [PASS] Duplicate request returned existing report {d_dup['id']} with HTTP 200 (idempotent).")

        # Call 2 with force_regenerate=True
        r_force = requests.post(f"{BASE_URL}/reports/generate/{pred_id}?force_regenerate=true", timeout=10)
        assert r_force.status_code == 201, f"Expected 201 Created on force_regenerate, got {r_force.status_code}"
        d_force = r_force.json()
        assert d_force["id"] != d_dup["id"], "force_regenerate failed to create a fresh report!"
        self.created_report_ids.append(d_force["id"])
        print(f"  [PASS] force_regenerate created fresh report {d_force['id']} with HTTP 201.")

    async def test_07_unknown_prediction_and_invalid_uuid_handling(self):
        """Test clean error handling for non-existent and malformed prediction / report UUIDs."""
        print("\n[Test 07] Testing Unknown & Malformed UUID Error Handling...")
        # 1. Unknown prediction ID -> 404
        r_unknown_pred = requests.post(f"{BASE_URL}/reports/generate/00000000-0000-0000-0000-000000000000", timeout=10)
        assert r_unknown_pred.status_code == 404
        assert "was not found" in r_unknown_pred.json()["detail"]

        # 2. Malformed prediction UUID -> 422
        r_bad_pred = requests.post(f"{BASE_URL}/reports/generate/not-a-valid-uuid", timeout=10)
        assert r_bad_pred.status_code == 422

        # 3. Unknown report ID -> 404
        r_unknown_rep = requests.get(f"{BASE_URL}/reports/00000000-0000-0000-0000-000000000000", timeout=10)
        assert r_unknown_rep.status_code == 404
        assert "was not found" in r_unknown_rep.json()["detail"]

        # 4. Malformed report UUID -> 422
        r_bad_rep = requests.get(f"{BASE_URL}/reports/invalid-uuid-syntax", timeout=10)
        assert r_bad_rep.status_code == 422

        print("  [PASS] Clean 404 and 422 handling verified for unknown and malformed UUIDs.")

    async def test_08_live_reports_listing_and_filtering(self):
        """Test GET /reports pagination and filtering by prediction_id, report_type, status, and invalid filters."""
        print("\n[Test 08] Testing Live GET /reports Listing & Filtering...")
        # 1. Listing all reports
        resp = requests.get(f"{BASE_URL}/reports", timeout=10)
        assert resp.status_code == 200
        d_all = resp.json()
        assert d_all["total_reports"] >= len(self.created_report_ids)
        assert len(d_all["reports"]) >= len(self.created_report_ids)

        # 2. Filter by prediction_id
        sample_rep_id = self.created_report_ids[0]
        rep_detail = requests.get(f"{BASE_URL}/reports/{sample_rep_id}", timeout=10).json()
        target_pred_id = rep_detail["prediction_id"]

        r_filter_pred = requests.get(f"{BASE_URL}/reports?prediction_id={target_pred_id}", timeout=10)
        assert r_filter_pred.status_code == 200
        d_fpred = r_filter_pred.json()
        assert d_fpred["total_reports"] >= 1
        for r in d_fpred["reports"]:
            assert str(r["prediction_id"]) == str(target_pred_id)

        # 3. Filter by report_type
        r_filter_type = requests.get(f"{BASE_URL}/reports?report_type=disease_diagnostic", timeout=10)
        assert r_filter_type.status_code == 200
        for r in r_filter_type.json()["reports"]:
            assert r["report_type"] == "disease_diagnostic"

        # 4. Filter by status
        r_filter_status = requests.get(f"{BASE_URL}/reports?status=completed", timeout=10)
        assert r_filter_status.status_code == 200
        for r in r_filter_status.json()["reports"]:
            assert r["status"] == "completed"

        # 5. Invalid query parameters
        r_inv_type = requests.get(f"{BASE_URL}/reports?report_type=invalid_category", timeout=10)
        assert r_inv_type.status_code == 400
        assert "Invalid report_type" in r_inv_type.json()["detail"]

        r_inv_status = requests.get(f"{BASE_URL}/reports?status=pending_review", timeout=10)
        assert r_inv_status.status_code == 400
        assert "Invalid status" in r_inv_status.json()["detail"]

        r_inv_pid = requests.get(f"{BASE_URL}/reports?prediction_id=not-a-uuid", timeout=10)
        assert r_inv_pid.status_code == 400
        assert "must be a valid UUID" in r_inv_pid.json()["detail"]

        print("  [PASS] Report listing, pagination, filters, and invalid parameter rejection verified.")

    async def test_09_database_rollback_on_persistence_failure(self):
        """Test that database error during report creation triggers clean rollback without corrupting session."""
        print("\n[Test 09] Testing Database Rollback on Persistence Failure...")
        session = AsyncSessionLocal()
        try:
            repo = ReportRepository(session)
            # Intentionally violate FK constraint by supplying a non-existent prediction_id
            fake_pred_uuid = uuid.uuid4()
            with assert_raises(Exception):
                await repo.create_report(
                    report_type="disease_diagnostic",
                    title="Rollback Test Report",
                    prediction_id=fake_pred_uuid,  # Invalid FK
                )
                await session.flush()

            await session.rollback()
            print("  [PASS] Foreign key failure caught and rolled back cleanly.")

            # Session remains functional
            cnt = await repo.count()
            assert cnt >= 0
            print("  [PASS] Session restored cleanly after rollback.")
        finally:
            await session.close()

    async def test_10_regression_prediction_and_market_apis_compatibility(self):
        """Verify prediction, market, and buyer APIs remain completely unaffected."""
        print("\n[Test 10] Testing Backward Compatibility & Unaffected Subsystems...")
        # 1. Health endpoint
        r_health = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r_health.status_code == 200

        # 2. Prediction history endpoint
        r_preds = requests.get(f"{BASE_URL}/predictions?page_size=5", timeout=10)
        assert r_preds.status_code == 200
        assert r_preds.json()["total_predictions"] == 35

        # 3. Market prices endpoint
        r_market = requests.get(f"{BASE_URL}/market/prices?page_size=5", timeout=10)
        assert r_market.status_code == 200
        assert r_market.json()["total"] >= 100

        # 4. Buyers endpoint
        r_buyers = requests.get(f"{BASE_URL}/buyers?page_size=5", timeout=10)
        assert r_buyers.status_code == 200
        assert r_buyers.json()["total"] == 17

        print("  [PASS] Predictions, Market, Buyer, and Health APIs verified 100% functional.")

    async def test_11_post_test_cleanup_and_baseline_integrity(self):
        """Clean up all test-generated reports and verify PostgreSQL returns strictly to baseline."""
        print("\n[Test 11] Cleaning Up Test Reports & Verifying Pristine Baseline...")
        session = AsyncSessionLocal()
        try:
            for rep_id in self.created_report_ids:
                u = uuid.UUID(rep_id)
                await session.execute(delete(Report).where(Report.id == u))
            await session.commit()
            print(f"  [PASS] Cleaned up {len(self.created_report_ids)} test report records.")
        finally:
            await session.close()

        # Verify all table counts strictly match baseline
        counts = await get_db_counts()
        for tbl, expected in EXPECTED_BASELINE_COUNTS.items():
            actual = counts[tbl]
            print(f"  Table '{tbl}': actual={actual}, expected={expected}")
            assert actual == expected, f"Table '{tbl}' count corrupted: {actual} != {expected}"

        print("  [PASS] All 7 database tables remain completely pristine with reports=0.")


async def main():
    print("=" * 80)
    print("STEP 11I.2 — DISEASE DETECTION REPORT GENERATION TEST SUITE")
    print("=" * 80)

    suite = Step11I2TestSuite()
    tests = [
        suite.test_01_database_baseline_integrity,
        suite.test_02_report_repository_validation_and_methods,
        suite.test_03_generate_report_from_real_image_only_prediction,
        suite.test_04_generate_report_from_real_multimodal_prediction,
        suite.test_05_privacy_and_security_leak_check,
        suite.test_06_duplicate_request_idempotency_and_force_regenerate,
        suite.test_07_unknown_prediction_and_invalid_uuid_handling,
        suite.test_08_live_reports_listing_and_filtering,
        suite.test_09_database_rollback_on_persistence_failure,
        suite.test_10_regression_prediction_and_market_apis_compatibility,
        suite.test_11_post_test_cleanup_and_baseline_integrity,
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
