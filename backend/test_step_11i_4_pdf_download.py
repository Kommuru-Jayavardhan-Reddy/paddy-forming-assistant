"""
Paddy Farming Assistant - STEP 11I.4 PDF Report Generation & Download Test Suite
================================================================================
Verifies ReportLab PDF generation, secure artifact storage, GET /reports/{id}/download,
safe Content-Disposition headers, missing/corrupted artifact self-healing, path traversal
defense, privacy protection (0 coordinates/paths leaked), and full regression.
"""

import asyncio
import io
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

from app import config
from app.db.session import AsyncSessionLocal
from app.db.models.prediction import PredictionHistory
from app.db.models.report import Report
from app.db.repositories.other_repositories import ReportRepository
from app.services.pdf_report_service import PDFReportService, resolve_report_path

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


class Step11I4TestSuite:
    """Comprehensive test suite for STEP 11I.4 PDF Generation & Download."""

    def __init__(self):
        self.created_report_ids: List[str] = []
        self.created_prediction_ids: List[str] = []
        self.created_disk_files: List[Path] = []

    async def test_01_database_baseline_integrity(self):
        """Verify pre-test database table row counts match expected baseline."""
        print("\n[Test 01] Verifying Pre-Test Database Baseline Counts...")
        counts = await get_db_counts()
        for tbl, expected in EXPECTED_BASELINE_COUNTS.items():
            actual = counts[tbl]
            print(f"  Table '{tbl}': actual={actual}, expected={expected}")
            assert actual == expected, f"Table '{tbl}' count mismatch: {actual} != {expected}"
        print("  [PASS] Baseline database counts verified (reports=0).")

    async def test_02_pdf_generation_from_image_only_prediction(self):
        """Generate PDF report for genuine image-only prediction and verify artifact on disk."""
        print("\n[Test 02] Testing PDF Generation from Image-Only Prediction...")
        r_pred = requests.get(f"{BASE_URL}/predictions?prediction_mode=image_only&page_size=1", timeout=10)
        assert r_pred.status_code == 200
        pred_item = r_pred.json()["predictions"][0]
        pred_id = pred_item["id"]

        r_gen = requests.post(f"{BASE_URL}/reports/generate/{pred_id}?file_format=pdf", timeout=10)
        assert r_gen.status_code == 201, f"Expected 201, got {r_gen.status_code}: {r_gen.text}"
        data = r_gen.json()
        rep_id = data["id"]
        self.created_report_ids.append(rep_id)

        assert data["file_format"] == "pdf"
        assert data["file_size_bytes"] > 0
        assert "file_path" not in data, "file_path leaked in public ReportResponse!"

        # Verify physical file existence in storage
        session = AsyncSessionLocal()
        try:
            repo = ReportRepository(session)
            db_rep = await repo.get_by_id(uuid.UUID(rep_id))
            assert db_rep is not None
            assert db_rep.file_format == "pdf"
            assert db_rep.file_path is not None

            disk_path = resolve_report_path(db_rep.file_path)
            assert disk_path.exists(), f"PDF artifact missing on disk: {disk_path}"
            self.created_disk_files.append(disk_path)

            with open(disk_path, "rb") as f:
                header = f.read(8)
            assert header.startswith(b"%PDF-"), f"Invalid PDF magic header on disk: {header}"

            print(f"  [PASS] Image-only PDF generated and persisted: {disk_path.name} ({db_rep.file_size_bytes} bytes).")
        finally:
            await session.close()

    async def test_03_pdf_generation_from_multimodal_prediction(self):
        """Generate PDF report for genuine multimodal prediction with 10-step attention."""
        print("\n[Test 03] Testing PDF Generation from Multimodal Prediction...")
        r_pred = requests.get(f"{BASE_URL}/predictions?prediction_mode=multimodal&page_size=1", timeout=10)
        assert r_pred.status_code == 200
        pred_item = r_pred.json()["predictions"][0]
        pred_id = pred_item["id"]

        r_gen = requests.post(f"{BASE_URL}/reports/generate/{pred_id}?file_format=pdf", timeout=10)
        assert r_gen.status_code == 201
        data = r_gen.json()
        rep_id = data["id"]
        self.created_report_ids.append(rep_id)

        session = AsyncSessionLocal()
        try:
            repo = ReportRepository(session)
            db_rep = await repo.get_by_id(uuid.UUID(rep_id))
            assert db_rep is not None
            disk_path = resolve_report_path(db_rep.file_path)
            assert disk_path.exists()
            self.created_disk_files.append(disk_path)

            meta = db_rep.report_metadata
            assert meta["prediction_mode"] == "multimodal"
            assert meta["attention_weights"] is not None
            assert len(meta["attention_weights"]) == 10

            print(f"  [PASS] Multimodal PDF generated with 10-step attention: {disk_path.name}")
        finally:
            await session.close()

    async def test_04_download_pdf_endpoint(self):
        """Test GET /reports/{report_id}/download endpoint headers, content-disposition, and binary bytes."""
        print("\n[Test 04] Testing GET /reports/{report_id}/download Endpoint...")
        rep_id = self.created_report_ids[0]

        r_dl = requests.get(f"{BASE_URL}/reports/{rep_id}/download", timeout=10)
        assert r_dl.status_code == 200, f"Download failed: {r_dl.status_code}: {r_dl.text}"

        # 1. Content-Type header
        assert "application/pdf" in r_dl.headers.get("content-type", "")

        # 2. Content-Disposition header
        disp = r_dl.headers.get("content-disposition", "")
        assert "attachment" in disp
        assert f"paddy_disease_report_{rep_id}.pdf" in disp

        # 3. PDF Header & Content validation
        pdf_bytes = r_dl.content
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-"), "Missing %PDF- header in response body!"
        assert b"%%EOF" in pdf_bytes[-1024:], "Missing %%EOF marker in PDF body!"

        # 4. Content-Length header
        assert str(len(pdf_bytes)) == r_dl.headers.get("content-length")

        print("  [PASS] Valid application/pdf received with safe Content-Disposition attachment header.")

    async def test_05_dynamic_pdf_compile_on_download_for_json_report(self):
        """Test that downloading a report originally created as JSON compiles PDF dynamically."""
        print("\n[Test 05] Testing Dynamic PDF Compilation on Download for JSON Report...")
        r_pred = requests.get(f"{BASE_URL}/predictions?page_size=10", timeout=10)
        preds = r_pred.json()["predictions"]
        candidate_pred = None
        for p in preds:
            if p["id"] not in self.created_prediction_ids:
                candidate_pred = p
                break
        assert candidate_pred is not None

        # 1. Generate strictly as JSON (with force_regenerate to guarantee 201)
        r_gen = requests.post(f"{BASE_URL}/reports/generate/{candidate_pred['id']}?file_format=json&force_regenerate=true", timeout=10)
        assert r_gen.status_code == 201, f"Expected 201, got {r_gen.status_code}: {r_gen.text}"
        rep_data = r_gen.json()
        rep_id = rep_data["id"]
        self.created_report_ids.append(rep_id)
        assert rep_data["file_format"] == "json"

        # 2. Call download endpoint
        r_dl = requests.get(f"{BASE_URL}/reports/{rep_id}/download", timeout=10)
        assert r_dl.status_code == 200
        assert "application/pdf" in r_dl.headers.get("content-type", "")
        assert r_dl.content.startswith(b"%PDF-")

        # 3. Verify database updated to PDF
        session = AsyncSessionLocal()
        try:
            repo = ReportRepository(session)
            db_rep = await repo.get_by_id(uuid.UUID(rep_id))
            assert db_rep is not None
            assert db_rep.file_format == "pdf"
            assert db_rep.file_path.endswith(".pdf")
            disk_path = resolve_report_path(db_rep.file_path)
            assert disk_path.exists()
            self.created_disk_files.append(disk_path)
            print(f"  [PASS] Dynamically compiled PDF for JSON report: {disk_path.name} ({len(r_dl.content)} bytes).")
        finally:
            await session.close()

    async def test_06_missing_artifact_self_healing(self):
        """Test that missing disk artifact is detected and safely regenerated from PostgreSQL metadata."""
        print("\n[Test 06] Testing Missing Disk Artifact Self-Healing...")
        rep_id = self.created_report_ids[0]

        session = AsyncSessionLocal()
        try:
            repo = ReportRepository(session)
            db_rep = await repo.get_by_id(uuid.UUID(rep_id))
            disk_path = resolve_report_path(db_rep.file_path)
            assert disk_path.exists()

            # Temporarily unlink the file to simulate missing artifact
            disk_path.unlink()
            assert not disk_path.exists(), "Failed to delete file for test!"

            # Direct read raises FileNotFoundError
            with assert_raises(FileNotFoundError, match="not found"):
                PDFReportService.read_pdf_artifact(db_rep.file_path)
            print("  [PASS] Direct read of missing artifact raised FileNotFoundError as expected.")

            # API download heals and regenerates the file cleanly
            r_dl = requests.get(f"{BASE_URL}/reports/{rep_id}/download", timeout=10)
            assert r_dl.status_code == 200
            assert r_dl.content.startswith(b"%PDF-")
            assert disk_path.exists(), "Self-healing failed to re-create missing PDF artifact!"
            print("  [PASS] Download API successfully healed and regenerated missing artifact.")
        finally:
            await session.close()

    async def test_07_corrupted_artifact_handling(self):
        """Test that corrupted artifact (missing PDF magic header) is detected and regenerated."""
        print("\n[Test 07] Testing Corrupted Artifact Detection & Recovery...")
        rep_id = self.created_report_ids[0]

        session = AsyncSessionLocal()
        try:
            repo = ReportRepository(session)
            db_rep = await repo.get_by_id(uuid.UUID(rep_id))
            disk_path = resolve_report_path(db_rep.file_path)

            # Corrupt the file on disk
            with open(disk_path, "wb") as f:
                f.write(b"CORRUPTED_NON_PDF_DATA_GARBAGE")

            # Direct read raises ValueError
            with assert_raises(ValueError, match="corrupted: missing PDF magic header"):
                PDFReportService.read_pdf_artifact(db_rep.file_path)
            print("  [PASS] Corrupted file rejected with ValueError on missing magic header.")

            # API download heals and recovers with a genuine PDF
            r_dl = requests.get(f"{BASE_URL}/reports/{rep_id}/download", timeout=10)
            assert r_dl.status_code == 200
            assert r_dl.content.startswith(b"%PDF-")
            print("  [PASS] Download API recovered from corrupted file by compiling fresh valid PDF.")
        finally:
            await session.close()

    async def test_08_error_handling_and_path_traversal_guards(self):
        """Test 404 for unknown report, 422 for malformed UUID, and strict path traversal guards."""
        print("\n[Test 08] Testing Error Handling & Path Traversal Guards...")
        # 1. Unknown report UUID -> 404
        r_404 = requests.get(f"{BASE_URL}/reports/00000000-0000-0000-0000-000000000000/download", timeout=10)
        assert r_404.status_code == 404
        assert "was not found" in r_404.json()["detail"]

        # 2. Malformed report UUID -> 422
        r_422 = requests.get(f"{BASE_URL}/reports/not-a-valid-uuid/download", timeout=10)
        assert r_422.status_code == 422

        # 3. Path traversal guards
        with assert_raises(ValueError, match="Path traversal is prohibited"):
            resolve_report_path("../../../windows/system32/cmd.exe")

        with assert_raises(ValueError, match="Path traversal is prohibited"):
            resolve_report_path("diagnostic/../../secret.txt")

        with assert_raises(ValueError, match="Path traversal is prohibited"):
            resolve_report_path("C:\\Windows\\win.ini")

        print("  [PASS] 404, 422, and path traversal defenses verified successfully.")

    async def test_09_privacy_and_security_leak_verification(self):
        """Verify downloaded PDF content and public API responses never expose coordinates or server paths."""
        print("\n[Test 09] Verifying Zero Privacy/Security Leaks in PDF & API Responses...")
        rep_id = self.created_report_ids[0]

        # 1. Downloaded PDF binary content
        r_dl = requests.get(f"{BASE_URL}/reports/{rep_id}/download", timeout=10)
        assert r_dl.status_code == 200
        pdf_raw = r_dl.content

        # Decode printable ASCII strings for inspection
        ascii_text = "".join(chr(b) for b in pdf_raw if 32 <= b <= 126)

        assert "image_storage_path" not in ascii_text, "image_storage_path leaked in PDF!"
        assert "gradcam_storage_path" not in ascii_text, "gradcam_storage_path leaked in PDF!"
        assert "reports_storage" not in ascii_text, "reports_storage path leaked in PDF!"
        assert "C:\\" not in ascii_text, "Windows filesystem path leaked in PDF!"
        assert "/home/" not in ascii_text, "Linux filesystem path leaked in PDF!"
        assert "postgresql://" not in ascii_text, "DB connection string leaked in PDF!"
        assert "latitude" not in ascii_text.lower(), "Latitude leaked in PDF!"
        assert "longitude" not in ascii_text.lower(), "Longitude leaked in PDF!"

        # 2. Public JSON ReportResponse schema
        r_get = requests.get(f"{BASE_URL}/reports/{rep_id}", timeout=10)
        assert r_get.status_code == 200
        json_data = r_get.json()
        assert "file_path" not in json_data, "file_path leaked in ReportResponse schema!"

        print("  [PASS] Zero raw GPS coordinates, server paths, or credentials leaked in PDF or API.")

    async def test_10_regression_all_subsystems(self):
        """Verify prediction history, disease detection, market, buyer, field, satellite, weather, and health APIs."""
        print("\n[Test 10] Testing Regression Across All Backend Subsystems...")
        # 1. Health API
        r_health = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r_health.status_code == 200

        # Database and Model Health APIs
        r_db_health = requests.get(f"{BASE_URL}/health/database", timeout=5)
        assert r_db_health.status_code == 200
        assert r_db_health.json()["status"] == "healthy"

        r_model_health = requests.get(f"{BASE_URL}/health/model", timeout=5)
        assert r_model_health.status_code == 200
        assert r_model_health.json()["status"] == "loaded"

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
        finally:
            if created_pred_id:
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

        # 6. Fields API
        r_fields = requests.get(f"{BASE_URL}/fields?page_size=5", timeout=10)
        assert r_fields.status_code == 200
        assert r_fields.json()["total_fields"] == 58

        # 7. Satellite Vegetation Time-Series API
        r_sat = requests.get(f"{BASE_URL}/fields/FIELD_01/timeseries", timeout=10)
        assert r_sat.status_code == 200

        # 8. Weather Subsystem Verification (read-only verification to avoid caching side-effects)
        session_wx = AsyncSessionLocal()
        try:
            from app.db.repositories.weather_repository import WeatherRepository
            wx_repo = WeatherRepository(session_wx)
            wx_cnt = await wx_repo.count()
            assert wx_cnt == 92, f"Expected 92 weather records, got {wx_cnt}"
        finally:
            await session_wx.close()

        print("  [PASS] All 8 subsystems (Health, Predictions, Disease AI, Market, Buyers, Fields, Satellite, Weather) 100% verified.")

    async def test_11_test_cleanup_and_post_test_baseline_verification(self):
        """Clean up all test-created report records and disk files; verify database returns strictly to baseline."""
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
            print(f"  [PASS] Cleaned up {len(self.created_report_ids)} test report records from PostgreSQL.")
        finally:
            await session.close()

        # Clean up disk files
        cleaned_files = 0
        for f in self.created_disk_files:
            try:
                if f.exists():
                    f.unlink()
                    cleaned_files += 1
            except Exception as e:
                logger.warning("Could not delete test file %s: %s", f, e)

        # Also clean any diagnostic report files matching test reports
        diag_dir = config.REPORTS_STORAGE_DIR / "diagnostic"
        if diag_dir.exists():
            for p in diag_dir.glob("report_*"):
                try:
                    p.unlink()
                    cleaned_files += 1
                except Exception:
                    pass

        print(f"  [PASS] Cleaned up {cleaned_files} test files from persistent disk storage.")

        # Verify all table counts strictly match baseline
        counts = await get_db_counts()
        for tbl, expected in EXPECTED_BASELINE_COUNTS.items():
            actual = counts[tbl]
            print(f"  Table '{tbl}': actual={actual}, expected={expected}")
            assert actual == expected, f"Table '{tbl}' count corrupted: {actual} != {expected}"

        print("  [PASS] All 7 database tables remain completely pristine with reports=0.")


async def main():
    print("=" * 80)
    print("STEP 11I.4 — SECURE PDF REPORT GENERATION & DOWNLOAD TEST SUITE")
    print("=" * 80)

    suite = Step11I4TestSuite()
    tests = [
        suite.test_01_database_baseline_integrity,
        suite.test_02_pdf_generation_from_image_only_prediction,
        suite.test_03_pdf_generation_from_multimodal_prediction,
        suite.test_04_download_pdf_endpoint,
        suite.test_05_dynamic_pdf_compile_on_download_for_json_report,
        suite.test_06_missing_artifact_self_healing,
        suite.test_07_corrupted_artifact_handling,
        suite.test_08_error_handling_and_path_traversal_guards,
        suite.test_09_privacy_and_security_leak_verification,
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
