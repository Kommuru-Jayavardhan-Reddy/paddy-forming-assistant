"""
Paddy Farming Assistant - STEP 11I.3 Report Retrieval API Test Suite
=====================================================================
Tests and verifies report retrieval endpoints (GET /reports, GET /reports/{report_id}),
pagination, filtering, UUID validation, stable ordering, database matching,
data integrity, privacy masking, duplicate idempotency, and full regression.
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


class Step11I3TestSuite:
    """Comprehensive test suite for STEP 11I.3 Report Retrieval API."""

    def __init__(self):
        self.created_report_ids: List[str] = []
        self.created_prediction_ids: List[str] = []

    async def test_01_database_baseline_integrity(self):
        """Verify pre-test database table row counts match expected baseline."""
        print("\n[Test 01] Verifying Pre-Test Database Baseline Counts...")
        counts = await get_db_counts()
        for tbl, expected in EXPECTED_BASELINE_COUNTS.items():
            actual = counts[tbl]
            print(f"  Table '{tbl}': actual={actual}, expected={expected}")
            assert actual == expected, f"Table '{tbl}' count mismatch: {actual} != {expected}"
        print("  [PASS] Baseline database counts verified (reports=0).")

    async def test_02_get_reports_empty_history(self):
        """Verify GET /reports returns 200 with empty list when no reports exist."""
        print("\n[Test 02] Testing GET /reports with Empty Report History...")
        resp = requests.get(f"{BASE_URL}/reports", timeout=10)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["reports"] == [], f"Expected empty reports list, got {data['reports']}"
        assert data["total_reports"] == 0, f"Expected total_reports 0, got {data['total_reports']}"
        assert data["page"] == 1
        assert data["page_size"] == 50
        print("  [PASS] Empty report history verified: returns total_reports=0 and empty reports array.")

    async def test_03_report_generation_and_retrieval_by_id(self):
        """Generate a report from a real image_only prediction and retrieve via GET /reports/{report_id}."""
        print("\n[Test 03] Testing Report Generation & Retrieval via GET /reports/{report_id}...")
        # 1. Fetch real image_only prediction
        r_pred = requests.get(f"{BASE_URL}/predictions?prediction_mode=image_only&page_size=1", timeout=10)
        assert r_pred.status_code == 200
        pred_item = r_pred.json()["predictions"][0]
        pred_id = pred_item["id"]

        # 2. Generate report
        r_gen = requests.post(f"{BASE_URL}/reports/generate/{pred_id}", timeout=10)
        assert r_gen.status_code == 201, f"Expected 201, got {r_gen.status_code}: {r_gen.text}"
        gen_data = r_gen.json()
        rep_id = gen_data["id"]
        self.created_report_ids.append(rep_id)

        # 3. Retrieve report via GET /reports/{report_id}
        r_get = requests.get(f"{BASE_URL}/reports/{rep_id}", timeout=10)
        assert r_get.status_code == 200, f"Expected 200, got {r_get.status_code}: {r_get.text}"
        get_data = r_get.json()

        # 4. Confirm API response matches generated data
        assert get_data["id"] == rep_id
        assert get_data["prediction_id"] == pred_id
        assert get_data["report_type"] == "disease_diagnostic"
        assert get_data["status"] == "completed"
        assert get_data["file_format"] == "json"
        assert get_data["file_size_bytes"] > 0
        assert get_data["title"] == gen_data["title"]
        assert get_data["summary"] == gen_data["summary"]

        # 5. Confirm report metadata matches source prediction
        meta = get_data["report_metadata"]
        assert meta["prediction_id"] == pred_id
        assert meta["predicted_disease"] == pred_item["predicted_disease"]
        assert abs(meta["confidence"] - pred_item["confidence"]) < 0.001
        assert meta["prediction_mode"] == "image_only"
        assert meta["model_name"] == pred_item["model_name"]
        assert meta["model_version"] == pred_item["model_version"]
        assert meta["image_sha256"] == pred_item["image_sha256"]
        assert "disclaimer" in meta
        assert "decision support" in meta["disclaimer"]

        # 6. Direct PostgreSQL verification
        session = AsyncSessionLocal()
        try:
            repo = ReportRepository(session)
            db_rep = await repo.get_by_id(uuid.UUID(rep_id))
            assert db_rep is not None, "Report not found directly in PostgreSQL!"
            assert str(db_rep.id) == rep_id
            assert str(db_rep.prediction_id) == pred_id
            assert db_rep.report_type == "disease_diagnostic"
            assert db_rep.status == "completed"
            assert db_rep.title == get_data["title"]
            assert db_rep.file_format == "json"
            assert db_rep.file_size_bytes == get_data["file_size_bytes"]
            assert db_rep.report_metadata["predicted_disease"] == pred_item["predicted_disease"]
            print("  [PASS] Retrieved report verified against both API response and direct PostgreSQL record.")
        finally:
            await session.close()

    async def test_04_get_reports_pagination_and_stable_ordering(self):
        """Test GET /reports pagination (limit, offset, pages) and deterministic descending ordering."""
        print("\n[Test 04] Testing GET /reports Pagination and Stable Ordering...")
        # Generate 2 additional reports from different predictions to have at least 3 reports
        r_preds = requests.get(f"{BASE_URL}/predictions?page_size=5", timeout=10)
        assert r_preds.status_code == 200
        preds = r_preds.json()["predictions"]

        for p in preds:
            if len(self.created_report_ids) >= 3:
                break
            if p["id"] == self.created_report_ids[0]:
                continue
            r_g = requests.post(f"{BASE_URL}/reports/generate/{p['id']}", timeout=10)
            if r_g.status_code in (200, 201):
                rid = r_g.json()["id"]
                if rid not in self.created_report_ids:
                    self.created_report_ids.append(rid)

        assert len(self.created_report_ids) >= 3, f"Need at least 3 reports for pagination test, have {len(self.created_report_ids)}"
        print(f"  Active test reports: {len(self.created_report_ids)}")

        # 1. Page 1 with page_size=2
        r_p1 = requests.get(f"{BASE_URL}/reports?page=1&page_size=2", timeout=10)
        assert r_p1.status_code == 200
        d_p1 = r_p1.json()
        assert len(d_p1["reports"]) == 2
        assert d_p1["total_reports"] >= 3
        assert d_p1["page"] == 1
        assert d_p1["page_size"] == 2

        # 2. Page 2 with page_size=2
        r_p2 = requests.get(f"{BASE_URL}/reports?page=2&page_size=2", timeout=10)
        assert r_p2.status_code == 200
        d_p2 = r_p2.json()
        assert len(d_p2["reports"]) >= 1
        assert d_p2["page"] == 2

        # 3. Confirm no overlap between Page 1 and Page 2
        p1_ids = {r["id"] for r in d_p1["reports"]}
        p2_ids = {r["id"] for r in d_p2["reports"]}
        overlap = p1_ids.intersection(p2_ids)
        assert len(overlap) == 0, f"Pagination overlap detected between page 1 and page 2: {overlap}"

        # 4. Verify stable ordering: descending created_at
        r_all = requests.get(f"{BASE_URL}/reports?page_size=50", timeout=10)
        assert r_all.status_code == 200
        all_reps = r_all.json()["reports"]
        for i in range(len(all_reps) - 1):
            t1 = datetime.fromisoformat(all_reps[i]["created_at"])
            t2 = datetime.fromisoformat(all_reps[i + 1]["created_at"])
            assert t1 >= t2, f"Ordering violation: report {i} ({t1}) is earlier than report {i+1} ({t2})"

        # 5. Out-of-bounds page returns empty reports list
        r_empty = requests.get(f"{BASE_URL}/reports?page=999&page_size=50", timeout=10)
        assert r_empty.status_code == 200
        assert r_empty.json()["reports"] == []
        assert r_empty.json()["total_reports"] >= 3

        # 6. Invalid pagination parameters return 422
        assert requests.get(f"{BASE_URL}/reports?page=0").status_code == 422
        assert requests.get(f"{BASE_URL}/reports?page_size=0").status_code == 422
        assert requests.get(f"{BASE_URL}/reports?page_size=201").status_code == 422

        print("  [PASS] Pagination, boundary handling, and stable descending ordering verified.")

    async def test_05_get_reports_filtering(self):
        """Test GET /reports query filters: prediction_id, field_id, report_type, status."""
        print("\n[Test 05] Testing GET /reports Filtering Capabilities...")
        sample_rep_id = self.created_report_ids[0]
        sample_rep = requests.get(f"{BASE_URL}/reports/{sample_rep_id}", timeout=10).json()
        target_pred_id = sample_rep["prediction_id"]
        target_field_id = sample_rep["field_id"]

        # 1. Filter by prediction_id
        r_pred_filter = requests.get(f"{BASE_URL}/reports?prediction_id={target_pred_id}", timeout=10)
        assert r_pred_filter.status_code == 200
        d_pred = r_pred_filter.json()
        assert d_pred["total_reports"] >= 1
        for r in d_pred["reports"]:
            assert r["prediction_id"] == target_pred_id

        # 2. Filter by non-matching prediction_id returns 0
        unknown_pred_id = "00000000-0000-0000-0000-000000000000"
        r_unknown_pred = requests.get(f"{BASE_URL}/reports?prediction_id={unknown_pred_id}", timeout=10)
        assert r_unknown_pred.status_code == 200
        assert r_unknown_pred.json()["total_reports"] == 0
        assert r_unknown_pred.json()["reports"] == []

        # 3. Filter by report_type
        r_type = requests.get(f"{BASE_URL}/reports?report_type=disease_diagnostic", timeout=10)
        assert r_type.status_code == 200
        assert r_type.json()["total_reports"] >= 1
        for r in r_type.json()["reports"]:
            assert r["report_type"] == "disease_diagnostic"

        # Non-matching report_type
        r_type_none = requests.get(f"{BASE_URL}/reports?report_type=field_health_summary", timeout=10)
        assert r_type_none.status_code == 200
        assert r_type_none.json()["total_reports"] == 0

        # 4. Filter by status
        r_status = requests.get(f"{BASE_URL}/reports?status=completed", timeout=10)
        assert r_status.status_code == 200
        assert r_status.json()["total_reports"] >= 1
        for r in r_status.json()["reports"]:
            assert r["status"] == "completed"

        r_status_gen = requests.get(f"{BASE_URL}/reports?status=generating", timeout=10)
        assert r_status_gen.status_code == 200
        assert r_status_gen.json()["total_reports"] == 0

        # 5. Filter by field_id if linked
        if target_field_id:
            r_fid = requests.get(f"{BASE_URL}/reports?field_id={target_field_id}", timeout=10)
            assert r_fid.status_code == 200
            for r in r_fid.json()["reports"]:
                assert r["field_id"] == target_field_id

        print("  [PASS] All GET /reports filters (prediction_id, field_id, report_type, status) verified.")

    async def test_06_invalid_filters_and_malformed_uuids(self):
        """Test clean error handling on GET /reports with invalid filter parameters."""
        print("\n[Test 06] Testing Invalid Filters and Malformed UUIDs on GET /reports...")
        # 1. Malformed prediction_id UUID -> 400 Bad Request
        r_bad_pred = requests.get(f"{BASE_URL}/reports?prediction_id=not-a-uuid", timeout=10)
        assert r_bad_pred.status_code == 400
        assert "must be a valid UUID" in r_bad_pred.json()["detail"]

        # 2. Invalid report_type -> 400 Bad Request
        r_bad_type = requests.get(f"{BASE_URL}/reports?report_type=drone_survey", timeout=10)
        assert r_bad_type.status_code == 400
        assert "Invalid report_type" in r_bad_type.json()["detail"]

        # 3. Invalid status -> 400 Bad Request
        r_bad_status = requests.get(f"{BASE_URL}/reports?status=pending_review", timeout=10)
        assert r_bad_status.status_code == 400
        assert "Invalid status" in r_bad_status.json()["detail"]

        print("  [PASS] Clean 400 Bad Request handling verified for invalid query filters.")

    async def test_07_get_report_by_id_errors(self):
        """Test GET /reports/{report_id} 404 for unknown UUID and 422 for malformed UUID."""
        print("\n[Test 07] Testing GET /reports/{report_id} Error Handling (404 and 422)...")
        # 1. Unknown valid UUID -> 404 Not Found
        r_404 = requests.get(f"{BASE_URL}/reports/00000000-0000-0000-0000-000000000000", timeout=10)
        assert r_404.status_code == 404
        assert "was not found" in r_404.json()["detail"]

        # 2. Malformed UUID -> 422 Unprocessable Entity
        r_422 = requests.get(f"{BASE_URL}/reports/invalid-uuid-syntax-string", timeout=10)
        assert r_422.status_code == 422

        print("  [PASS] Verified 404 for non-existent report and 422 for malformed UUID.")

    async def test_08_privacy_and_security_leak_verification(self):
        """Verify report retrieval endpoints never expose raw GPS coordinates, private paths, or secrets."""
        print("\n[Test 08] Verifying Zero Privacy/Security Leaks in Report Retrieval...")
        sample_rep_id = self.created_report_ids[0]

        # 1. Single report endpoint
        r_single = requests.get(f"{BASE_URL}/reports/{sample_rep_id}", timeout=10)
        assert r_single.status_code == 200
        data_single = r_single.json()
        text_single = r_single.text

        assert "file_path" not in data_single, "file_path leaked in ReportResponse!"
        assert "image_storage_path" not in text_single, "image_storage_path leaked!"
        assert "gradcam_storage_path" not in text_single, "gradcam_storage_path leaked!"
        assert "C:\\" not in text_single, "Windows filesystem path leaked!"
        assert "/home/" not in text_single, "Linux filesystem path leaked!"
        assert "password" not in text_single.lower(), "Password keyword found in response!"
        assert "postgresql://" not in text_single, "DB connection string leaked!"
        assert "latitude" not in text_single.lower(), "Latitude leaked in report response!"
        assert "longitude" not in text_single.lower(), "Longitude leaked in report response!"

        # 2. List reports endpoint
        r_list = requests.get(f"{BASE_URL}/reports", timeout=10)
        assert r_list.status_code == 200
        text_list = r_list.text

        assert "file_path" not in text_list, "file_path leaked in list response!"
        assert "image_storage_path" not in text_list, "image_storage_path leaked in list response!"
        assert "gradcam_storage_path" not in text_list, "gradcam_storage_path leaked in list response!"
        assert "C:\\" not in text_list, "Windows filesystem path leaked in list response!"
        assert "latitude" not in text_list.lower(), "Latitude leaked in list response!"
        assert "longitude" not in text_list.lower(), "Longitude leaked in list response!"

        print("  [PASS] Verified complete masking: 0 raw GPS coordinates, server paths, or credentials leaked.")

    async def test_09_multimodal_data_integrity_and_duplicate_handling(self):
        """Test multimodal report generation, 10-step attention weights, and duplicate idempotency."""
        print("\n[Test 09] Testing Multimodal Data Integrity and Idempotency...")
        # 1. Fetch multimodal prediction
        r_multi = requests.get(f"{BASE_URL}/predictions?prediction_mode=multimodal&page_size=1", timeout=10)
        assert r_multi.status_code == 200
        multi_pred = r_multi.json()["predictions"][0]
        multi_id = multi_pred["id"]

        # 2. Generate report
        r_gen = requests.post(f"{BASE_URL}/reports/generate/{multi_id}", timeout=10)
        assert r_gen.status_code in (200, 201)
        gen_data = r_gen.json()
        report_id_1 = gen_data["id"]
        if report_id_1 not in self.created_report_ids:
            self.created_report_ids.append(report_id_1)

        # 3. Verify multimodal attributes in retrieved report
        r_fetch = requests.get(f"{BASE_URL}/reports/{report_id_1}", timeout=10)
        assert r_fetch.status_code == 200
        fetch_data = r_fetch.json()
        meta = fetch_data["report_metadata"]
        assert meta["prediction_mode"] == "multimodal"
        assert meta["model_name"] == "TemporalCrossAttention"
        assert meta["attention_weights"] is not None
        assert len(meta["attention_weights"]) == 10

        # 4. Duplicate request without force_regenerate returns HTTP 200 and same report ID
        r_dup = requests.post(f"{BASE_URL}/reports/generate/{multi_id}", timeout=10)
        assert r_dup.status_code == 200, f"Expected 200 OK on duplicate, got {r_dup.status_code}"
        assert r_dup.json()["id"] == report_id_1

        # 5. Duplicate request with force_regenerate=true returns HTTP 201 with new report ID
        r_force = requests.post(f"{BASE_URL}/reports/generate/{multi_id}?force_regenerate=true", timeout=10)
        assert r_force.status_code == 201
        report_id_2 = r_force.json()["id"]
        assert report_id_2 != report_id_1
        self.created_report_ids.append(report_id_2)

        # 6. Listing by prediction_id returns both reports ordered by created_at DESC
        r_list_pred = requests.get(f"{BASE_URL}/reports?prediction_id={multi_id}", timeout=10)
        assert r_list_pred.status_code == 200
        preds_reps = r_list_pred.json()["reports"]
        assert len(preds_reps) >= 2
        returned_ids = [r["id"] for r in preds_reps]
        assert report_id_2 in returned_ids
        assert report_id_1 in returned_ids
        # Newer report is first
        assert returned_ids.index(report_id_2) < returned_ids.index(report_id_1)

        print("  [PASS] Multimodal report integrity, 10-step attention, and duplicate idempotency verified.")

    async def test_10_regression_all_subsystems(self):
        """Verify prediction history, disease detection, market, buyer, field, satellite, weather, and health APIs."""
        print("\n[Test 10] Testing Regression Across All Backend Subsystems...")
        # 1. Health API
        r_health = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "healthy"

        # 2. Prediction History API
        r_preds = requests.get(f"{BASE_URL}/predictions?page_size=5", timeout=10)
        assert r_preds.status_code == 200
        assert r_preds.json()["total_predictions"] == 35

        # 3. Disease Detection API (live inference on real leaf)
        assert TEST_IMAGE_PATH.exists(), f"Missing test leaf image: {TEST_IMAGE_PATH}"
        with open(TEST_IMAGE_PATH, "rb") as f:
            img_bytes = f.read()

        created_pred_id = None
        try:
            files = {"file": ("test_leaf.jpg", img_bytes, "image/jpeg")}
            data = {"field_id": "FIELD_01", "question": "Are these spots normal?"}
            r_infer = requests.post(f"{BASE_URL}/predict", files=files, data=data, timeout=20)
            assert r_infer.status_code == 200
            infer_data = r_infer.json()
            assert "disease" in infer_data
            assert "confidence" in infer_data
            created_pred_id = infer_data.get("prediction_id")
            if created_pred_id:
                self.created_prediction_ids.append(created_pred_id)
                # Verify immediate single prediction lookup
                r_get_p = requests.get(f"{BASE_URL}/predictions/{created_pred_id}", timeout=10)
                assert r_get_p.status_code == 200
        finally:
            if created_pred_id:
                # Clean up this single inference record immediately
                session = AsyncSessionLocal()
                try:
                    await session.execute(
                        delete(PredictionHistory).where(PredictionHistory.id == uuid.UUID(created_pred_id))
                    )
                    await session.commit()
                    self.created_prediction_ids.remove(created_pred_id)
                finally:
                    await session.close()

        # 4. Market Prices API
        r_market = requests.get(f"{BASE_URL}/market/prices?page_size=5", timeout=10)
        assert r_market.status_code == 200
        assert r_market.json()["total"] >= 100

        # Market Trends API
        r_trends = requests.get(f"{BASE_URL}/market/analytics/trends?state=Karnataka&district=Dharwad", timeout=10)
        assert r_trends.status_code == 200

        # 5. Buyers API
        r_buyers = requests.get(f"{BASE_URL}/buyers?page_size=5", timeout=10)
        assert r_buyers.status_code == 200
        assert r_buyers.json()["total"] == 17

        # Buyers Nearby API
        r_nearby = requests.get(f"{BASE_URL}/buyers/nearby?lat=15.45&lon=75.00&radius_km=100", timeout=10)
        assert r_nearby.status_code == 200
        assert "items" in r_nearby.json()

        # 6. Fields API
        r_fields = requests.get(f"{BASE_URL}/fields?page_size=5", timeout=10)
        assert r_fields.status_code == 200
        assert r_fields.json()["total_fields"] == 58

        # 7. Satellite Vegetation Time-Series API
        r_sat = requests.get(f"{BASE_URL}/fields/FIELD_01/timeseries", timeout=10)
        assert r_sat.status_code == 200
        sat_data = r_sat.json()
        assert "timeseries" in sat_data or "sequence" in sat_data or "field_id" in sat_data

        # 8. Weather Subsystem Verification (read-only verification to avoid caching side-effects)
        session_wx = AsyncSessionLocal()
        try:
            from app.db.repositories.weather_repository import WeatherRepository
            wx_repo = WeatherRepository(session_wx)
            wx_cnt = await wx_repo.count()
            assert wx_cnt == 92, f"Expected 92 weather records, got {wx_cnt}"
        finally:
            await session_wx.close()

        # Database and Model Health APIs
        r_db_health = requests.get(f"{BASE_URL}/health/database", timeout=5)
        assert r_db_health.status_code == 200
        assert r_db_health.json()["status"] == "healthy"
        assert r_db_health.json()["connected"] is True

        r_model_health = requests.get(f"{BASE_URL}/health/model", timeout=5)
        assert r_model_health.status_code == 200
        assert r_model_health.json()["status"] == "loaded"

        print("  [PASS] All 8 subsystems (Health, Predictions, Disease AI, Market, Buyers, Fields, Satellite, Weather) 100% verified.")

    async def test_11_test_cleanup_and_post_test_baseline_verification(self):
        """Clean up all test-created report records and verify database returns strictly to baseline."""
        print("\n[Test 11] Cleaning Up Test Reports & Verifying Pristine Baseline...")
        session = AsyncSessionLocal()
        try:
            for rep_id in self.created_report_ids:
                u = uuid.UUID(rep_id)
                await session.execute(delete(Report).where(Report.id == u))

            for pid in self.created_prediction_ids:
                u = uuid.UUID(pid)
                await session.execute(delete(PredictionHistory).where(PredictionHistory.id == u))

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
    print("STEP 11I.3 — REPORT RETRIEVAL API AUDIT, TESTING & VERIFICATION")
    print("=" * 80)

    suite = Step11I3TestSuite()
    tests = [
        suite.test_01_database_baseline_integrity,
        suite.test_02_get_reports_empty_history,
        suite.test_03_report_generation_and_retrieval_by_id,
        suite.test_04_get_reports_pagination_and_stable_ordering,
        suite.test_05_get_reports_filtering,
        suite.test_06_invalid_filters_and_malformed_uuids,
        suite.test_07_get_report_by_id_errors,
        suite.test_08_privacy_and_security_leak_verification,
        suite.test_09_multimodal_data_integrity_and_duplicate_handling,
        suite.test_10_regression_all_subsystems,
        suite.test_11_test_cleanup_and_post_test_baseline_verification,
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
