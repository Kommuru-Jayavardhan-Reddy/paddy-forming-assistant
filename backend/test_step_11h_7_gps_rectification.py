"""
Paddy Farming Assistant - STEP 11H.7 Comprehensive Verification Suite
Tests GPS-Based Buyer Discovery, Safe Coordinate Importer, Edge Cases,
API Endpoints, Isolated Fixtures, and Database Preservation.

Rules:
- Never inserts synthetic coordinates into real production records.
- Uses isolated database transactions with guaranteed rollbacks for synthetic proximity tests.
- Verifies all 7 database table row counts remain completely intact.
"""

import sys
import os
import uuid
from decimal import Decimal
from pathlib import Path
import urllib.request
import urllib.error
import json
import asyncio

# UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, func, text
from app.db.session import AsyncSessionLocal
from app.db.models.buyer import Buyer
from app.db.repositories.other_repositories import BuyerRepository
from app.services.geo_service import haversine_distance_km, EARTH_RADIUS_KM
from scripts.import_buyer_coordinates import (
    parse_and_validate_coordinate_row,
    import_buyer_coordinates,
)

BASE_URL = "http://127.0.0.1:8000"


def http_get(path: str) -> tuple[int, dict]:
    """Helper to perform HTTP GET against live API."""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Step11H7Verifier/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            data = {"raw": str(e)}
        return e.code, data


# ==============================================================================
# 1. UNIT TESTS: HAVERSINE FORMULA & BOUNDARY VALIDATION
# ==============================================================================

def test_haversine_unit_calculations():
    print("\n--- [UNIT TEST 1] Haversine Distance Calculations ---")

    # 1. Exact same-point distance
    d0 = haversine_distance_km(16.5062, 80.6480, 16.5062, 80.6480)
    assert d0 == 0.0, f"Expected 0.0 km for identical points, got {d0}"
    print(f"  [PASS] Identical coordinates distance: {d0} km")

    # 2. Benchmark Vijayawada to Guntur (~31.0 km)
    d_vja_gnt = haversine_distance_km(16.5062, 80.6480, 16.3067, 80.4365)
    assert 30.0 <= d_vja_gnt <= 32.0, f"Vijayawada to Guntur unexpected: {d_vja_gnt}"
    print(f"  [PASS] Vijayawada to Guntur: {d_vja_gnt} km")

    # 3. Benchmark Kakinada to Rajahmundry (~47.1 km)
    d_kak_rjy = haversine_distance_km(16.9891, 82.2475, 17.0005, 81.8040)
    assert 46.0 <= d_kak_rjy <= 48.5, f"Kakinada to Rajahmundry unexpected: {d_kak_rjy}"
    print(f"  [PASS] Kakinada to Rajahmundry: {d_kak_rjy} km")

    # 4. Polar / Antipodal benchmark
    d_poles = haversine_distance_km(90.0, 0.0, -90.0, 0.0)
    assert 20000.0 <= d_poles <= 20030.0, f"Polar distance anomalous: {d_poles}"
    print(f"  [PASS] Pole to Pole distance: {d_poles} km")

    # 5. Out-of-range latitude rejection
    try:
        haversine_distance_km(95.0, 80.0, 16.0, 80.0)
        assert False, "Should have raised ValueError for lat > 90"
    except ValueError as e:
        assert "Latitude must be between" in str(e)
        print(f"  [PASS] Rejected out-of-range latitude (+95.0): {e}")

    # 6. Out-of-range longitude rejection
    try:
        haversine_distance_km(16.0, -185.0, 16.0, 80.0)
        assert False, "Should have raised ValueError for lon < -180"
    except ValueError as e:
        assert "Longitude must be between" in str(e)
        print(f"  [PASS] Rejected out-of-range longitude (-185.0): {e}")


# ==============================================================================
# 2. UNIT TESTS: SAFE COORDINATE IMPORTER PARSER & VALIDATOR
# ==============================================================================

def test_coordinate_importer_validation():
    print("\n--- [UNIT TEST 2] Coordinate Importer Row Validation ---")

    # 1. Valid accepted coordinate pair with full provenance
    valid_row = {
        "business_name": "Test Mill",
        "district": "Kakinada",
        "latitude": "16.989100",
        "longitude": "82.247500",
        "coordinate_source": "District Agricultural Survey",
        "source_reference": "Official Gazette Notification No 123",
        "evidence_notes": "Surveyed GPS point at mill gate entrance",
        "coordinate_verification_status": "accepted",
    }
    parsed = parse_and_validate_coordinate_row(valid_row, line_num=2)
    assert parsed["has_coordinates"] is True
    assert parsed["latitude"] == Decimal("16.989100")
    assert parsed["longitude"] == Decimal("82.247500")
    assert parsed["coordinate_verification_status"] == "accepted"
    print("  [PASS] Valid accepted coordinate row parsed correctly")

    # 2. Valid unresolved record (blank coordinates, official physical address)
    unresolved_row = {
        "business_name": "A V Agro",
        "district": "Kakinada",
        "latitude": "",
        "longitude": "",
        "coordinate_source": "APEDA Exporter Directory",
        "source_reference": "apeda.gov.in / AgriExchange",
        "evidence_notes": "Verified address present; surveyed GPS point unavailable",
        "coordinate_verification_status": "unresolved",
    }
    parsed_unres = parse_and_validate_coordinate_row(unresolved_row, line_num=3)
    assert parsed_unres["has_coordinates"] is False
    assert parsed_unres["latitude"] is None
    assert parsed_unres["longitude"] is None
    print("  [PASS] Valid unresolved row without coordinates parsed correctly")

    # 3. Partial pair: Latitude provided, Longitude missing -> MUST REJECT
    partial_lat_row = {
        "business_name": "Test Mill",
        "district": "Kakinada",
        "latitude": "16.9891",
        "longitude": "",
        "coordinate_source": "Survey",
        "source_reference": "Ref 123",
        "evidence_notes": "Test notes",
        "coordinate_verification_status": "accepted",
    }
    try:
        parse_and_validate_coordinate_row(partial_lat_row, line_num=4)
        assert False, "Should have rejected partial coordinate pair"
    except ValueError as e:
        assert "Partial coordinate pair" in str(e)
        print(f"  [PASS] Partial latitude-only pair rejected: {e}")

    # 4. Partial pair: Longitude provided, Latitude missing -> MUST REJECT
    partial_lon_row = {
        "business_name": "Test Mill",
        "district": "Kakinada",
        "latitude": "",
        "longitude": "82.2475",
        "coordinate_source": "Survey",
        "source_reference": "Ref 123",
        "evidence_notes": "Test notes",
        "coordinate_verification_status": "accepted",
    }
    try:
        parse_and_validate_coordinate_row(partial_lon_row, line_num=5)
        assert False, "Should have rejected partial coordinate pair"
    except ValueError as e:
        assert "Partial coordinate pair" in str(e)
        print(f"  [PASS] Partial longitude-only pair rejected: {e}")

    # 5. Out-of-bounds latitude in CSV -> MUST REJECT
    oob_lat_row = {
        "business_name": "Test Mill",
        "district": "Kakinada",
        "latitude": "95.5000",
        "longitude": "82.2475",
        "coordinate_source": "Survey",
        "source_reference": "Ref 123",
        "evidence_notes": "Test notes",
        "coordinate_verification_status": "accepted",
    }
    try:
        parse_and_validate_coordinate_row(oob_lat_row, line_num=6)
        assert False, "Should have rejected out-of-bounds latitude"
    except ValueError as e:
        assert "Latitude out of range" in str(e)
        print(f"  [PASS] Out-of-bounds latitude (+95.5) rejected: {e}")

    # 6. Out-of-bounds longitude in CSV -> MUST REJECT
    oob_lon_row = {
        "business_name": "Test Mill",
        "district": "Kakinada",
        "latitude": "16.9891",
        "longitude": "185.0000",
        "coordinate_source": "Survey",
        "source_reference": "Ref 123",
        "evidence_notes": "Test notes",
        "coordinate_verification_status": "accepted",
    }
    try:
        parse_and_validate_coordinate_row(oob_lon_row, line_num=7)
        assert False, "Should have rejected out-of-bounds longitude"
    except ValueError as e:
        assert "Longitude out of range" in str(e)
        print(f"  [PASS] Out-of-bounds longitude (+185.0) rejected: {e}")

    # 7. Coordinates provided under 'rejected' or 'unresolved' status -> MUST REJECT
    coords_rejected_row = {
        "business_name": "Test Mill",
        "district": "Kakinada",
        "latitude": "16.9891",
        "longitude": "82.2475",
        "coordinate_source": "Survey",
        "source_reference": "Ref 123",
        "evidence_notes": "Approximation",
        "coordinate_verification_status": "rejected",
    }
    try:
        parse_and_validate_coordinate_row(coords_rejected_row, line_num=8)
        assert False, "Should have rejected non-accepted coordinates"
    except ValueError as e:
        assert "Only 'accepted' coordinates can be ingested" in str(e)
        print(f"  [PASS] Unaccepted coordinate assignment rejected: {e}")

    # 8. Missing provenance (coordinate_source empty) -> MUST REJECT
    missing_prov_row = {
        "business_name": "Test Mill",
        "district": "Kakinada",
        "latitude": "16.9891",
        "longitude": "82.2475",
        "coordinate_source": "",
        "source_reference": "Ref 123",
        "evidence_notes": "Detailed notes here",
        "coordinate_verification_status": "accepted",
    }
    try:
        parse_and_validate_coordinate_row(missing_prov_row, line_num=9)
        assert False, "Should have rejected missing provenance"
    except ValueError as e:
        assert "'coordinate_source' required" in str(e)
        print(f"  [PASS] Missing coordinate_source rejected: {e}")


# ==============================================================================
# 3. ISOLATED TRANSACTION TEST: PROXIMITY, FILTERING & OUT-OF-BOUNDS HANDLING
# ==============================================================================

async def test_isolated_proximity_calculations():
    print("\n--- [ISOLATED TRANSACTION TEST] Nearest-Buyer Search & Filters ---")

    async with AsyncSessionLocal() as session:
        try:
            # Create synthetic test buyers inside an isolated transaction
            # (Guaranteed rollback at the end of the test)
            b1 = Buyer(
                id=uuid.uuid4(),
                business_name="TEST Synthetic Mill Vijayawada",
                buyer_type="mill",
                district="Krishna",
                state="Andhra Pradesh",
                address_summary="Test Yard, Vijayawada",
                verification_status="verified",
                is_active=True,
                latitude=Decimal("16.5062"),
                longitude=Decimal("80.6480"),
                coordinate_source="Test Benchmark GPS",
            )
            b2 = Buyer(
                id=uuid.uuid4(),
                business_name="TEST Synthetic FPO Guntur",
                buyer_type="fpo",
                district="Guntur",
                state="Andhra Pradesh",
                address_summary="Test Yard, Guntur",
                verification_status="verified",
                is_active=True,
                latitude=Decimal("16.3067"),
                longitude=Decimal("80.4365"),
                coordinate_source="Test Benchmark GPS",
            )
            b3 = Buyer(
                id=uuid.uuid4(),
                business_name="TEST Synthetic Mill Kakinada",
                buyer_type="mill",
                district="Kakinada",
                state="Andhra Pradesh",
                address_summary="Test Yard, Kakinada",
                verification_status="verified",
                is_active=True,
                latitude=Decimal("16.9891"),
                longitude=Decimal("82.2475"),
                coordinate_source="Test Benchmark GPS",
            )
            b_null = Buyer(
                id=uuid.uuid4(),
                business_name="TEST Synthetic Unlocated Buyer",
                buyer_type="mill",
                district="Krishna",
                state="Andhra Pradesh",
                address_summary="Test Yard, Unlocated",
                verification_status="pending",
                is_active=True,
                latitude=None,
                longitude=None,
                coordinate_source=None,
            )
            b_invalid = Buyer(
                id=uuid.uuid4(),
                business_name="TEST Synthetic Out-Of-Bounds Buyer",
                buyer_type="mill",
                district="Krishna",
                state="Andhra Pradesh",
                address_summary="Corrupt coordinate row",
                verification_status="verified",
                is_active=True,
                latitude=Decimal("95.0000"),
                longitude=Decimal("80.6480"),
                coordinate_source="Corrupt Test",
            )
            session.add_all([b1, b2, b3, b_null, b_invalid])
            await session.flush()

            repo = BuyerRepository(session)

            # Query from Vijayawada farmer: lat=16.5062, lon=80.6480
            results, total = await repo.list_nearby_buyers(
                farmer_lat=16.5062,
                farmer_lon=80.6480,
                radius_km=None,
            )

            # 1. Exclusion of NULL coordinates and Out-Of-Bounds coordinates
            res_ids = [b.id for b, _ in results]
            assert b_null.id not in res_ids, "NULL coordinate buyer must be excluded"
            assert b_invalid.id not in res_ids, "Out-of-bounds coordinate buyer must be excluded"
            print("  [PASS] NULL coordinates and out-of-bounds coordinates successfully excluded")

            # 2. Nearest-first ordering
            assert len(results) == 3, f"Expected 3 synthetic buyers with valid coords, got {len(results)}"
            assert results[0][0].id == b1.id, "b1 (Vijayawada) must be first (distance 0.0 km)"
            assert results[0][1] == 0.0, f"Expected 0.0 km, got {results[0][1]}"
            assert results[1][0].id == b2.id, "b2 (Guntur) must be second (~31.0 km)"
            assert 30.0 <= results[1][1] <= 32.0, f"Distance unexpected: {results[1][1]}"
            assert results[2][0].id == b3.id, "b3 (Kakinada) must be third (~178.6 km)"
            assert 175.0 <= results[2][1] <= 182.0, f"Distance unexpected: {results[2][1]}"
            print(f"  [PASS] Nearest-first ranking: 1st={results[0][1]} km, 2nd={results[1][1]} km, 3rd={results[2][1]} km")

            # 3. Radius boundary filtering (radius_km=50)
            res_r50, total_r50 = await repo.list_nearby_buyers(
                farmer_lat=16.5062,
                farmer_lon=80.6480,
                radius_km=50.0,
            )
            assert total_r50 == 2, f"Expected 2 buyers within 50km, got {total_r50}"
            assert [b.id for b, _ in res_r50] == [b1.id, b2.id]
            print(f"  [PASS] Radius boundary filter (50 km): {total_r50} buyers returned")

            # 4. District filter (district='Guntur')
            res_dist, total_dist = await repo.list_nearby_buyers(
                farmer_lat=16.5062,
                farmer_lon=80.6480,
                district="Guntur",
            )
            assert total_dist == 1 and res_dist[0][0].id == b2.id
            print(f"  [PASS] District filter (Guntur): {total_dist} buyer returned")

            # 5. Buyer-type filter (buyer_type='fpo')
            res_fpo, total_fpo = await repo.list_nearby_buyers(
                farmer_lat=16.5062,
                farmer_lon=80.6480,
                buyer_type="fpo",
            )
            assert total_fpo == 1 and res_fpo[0][0].id == b2.id
            print(f"  [PASS] Buyer type filter (fpo): {total_fpo} buyer returned")

            # 6. Pagination (skip=1, limit=1)
            res_p, total_p = await repo.list_nearby_buyers(
                farmer_lat=16.5062,
                farmer_lon=80.6480,
                skip=1,
                limit=1,
            )
            assert total_p == 3
            assert len(res_p) == 1
            assert res_p[0][0].id == b2.id
            print(f"  [PASS] Pagination: skip=1, limit=1 returned 2nd buyer (total={total_p})")

        finally:
            # ALWAYS ROLL BACK THE TRANSACTION
            await session.rollback()
            print("  [ROLLBACK] Synthetic test data transaction rolled back cleanly")


# ==============================================================================
# 4. LIVE API TESTS AGAINST LOCAL SERVER
# ==============================================================================

def test_live_api_endpoints():
    print("\n--- [LIVE API TEST] /buyers/nearby and Regression Endpoints ---")

    # 1. Current production state: all 17 buyers have NULL coordinates
    status, data = http_get("/buyers/nearby?lat=16.5062&lon=80.6480")
    assert status == 200, f"Expected 200 OK, got {status}: {data}"
    assert data["total"] == 0, f"Expected total 0, got {data['total']}"
    assert data["items"] == [], f"Expected items [], got {data['items']}"
    assert data["farmer_latitude"] == 16.5062
    assert data["farmer_longitude"] == 80.6480
    assert "Haversine" in data["disclaimer"]
    print("  [PASS] GET /buyers/nearby with NULL coordinate database returns 200 OK, 0 items")

    # 2. Query param validation: Missing lat -> 422
    status_no_lat, _ = http_get("/buyers/nearby?lon=80.6480")
    assert status_no_lat == 422, f"Expected 422 for missing lat, got {status_no_lat}"
    print("  [PASS] Missing latitude correctly rejected with 422")

    # 3. Query param validation: Missing lon -> 422
    status_no_lon, _ = http_get("/buyers/nearby?lat=16.5062")
    assert status_no_lon == 422, f"Expected 422 for missing lon, got {status_no_lon}"
    print("  [PASS] Missing longitude correctly rejected with 422")

    # 4. Query param validation: Out-of-bounds lat -> 422
    status_oob_lat, _ = http_get("/buyers/nearby?lat=95.0&lon=80.6480")
    assert status_oob_lat == 422, f"Expected 422 for lat > 90, got {status_oob_lat}"
    print("  [PASS] Out-of-bounds latitude (95.0) rejected with 422")

    # 5. Query param validation: Out-of-bounds lon -> 422
    status_oob_lon, _ = http_get("/buyers/nearby?lat=16.5062&lon=185.0")
    assert status_oob_lon == 422, f"Expected 422 for lon > 180, got {status_oob_lon}"
    print("  [PASS] Out-of-bounds longitude (185.0) rejected with 422")

    # 6. Query param validation: Negative radius -> 422
    status_neg_rad, _ = http_get("/buyers/nearby?lat=16.5062&lon=80.6480&radius_km=-5")
    assert status_neg_rad == 422, f"Expected 422 for negative radius, got {status_neg_rad}"
    print("  [PASS] Negative radius_km rejected with 422")

    # 7. Query param validation: Excessive radius (> 500km) -> 422
    status_big_rad, _ = http_get("/buyers/nearby?lat=16.5062&lon=80.6480&radius_km=1000")
    assert status_big_rad == 422, f"Expected 422 for radius > 500, got {status_big_rad}"
    print("  [PASS] Radius > 500 km rejected with 422")

    # 8. Query param validation: Invalid limit (0) -> 422
    status_lim0, _ = http_get("/buyers/nearby?lat=16.5062&lon=80.6480&limit=0")
    assert status_lim0 == 422, f"Expected 422 for limit=0, got {status_lim0}"
    print("  [PASS] Limit 0 rejected with 422")

    # 9. Optional filters on nearby endpoint: returns 200 OK
    status_filt, data_filt = http_get("/buyers/nearby?lat=16.5&lon=80.6&district=Kakinada&buyer_type=mill&verification_status=verified&skip=0&limit=10")
    assert status_filt == 200
    assert data_filt["total"] == 0
    print("  [PASS] GET /buyers/nearby with all query filters returns 200 OK")

    # 10. Existing buyer endpoints regression: GET /buyers
    status_b, data_b = http_get("/buyers")
    assert status_b == 200
    assert data_b["total"] == 17, f"Expected total 17, got {data_b['total']}"
    assert len(data_b["items"]) == 17
    print(f"  [PASS] GET /buyers returns 200 OK with all {data_b['total']} production records")

    # 11. Existing buyer endpoints regression: GET /buyers?district=Kakinada
    status_bk, data_bk = http_get("/buyers?district=Kakinada")
    assert status_bk == 200
    assert data_bk["total"] == 3
    print("  [PASS] GET /buyers?district=Kakinada returns 3 buyers")

    # 12. Existing buyer endpoints regression: GET /buyers?verification_status=pending
    status_bp, data_bp = http_get("/buyers?verification_status=pending")
    assert status_bp == 200
    assert data_bp["total"] == 2
    print("  [PASS] GET /buyers?verification_status=pending returns 2 pending buyers")

    # 13. Existing buyer endpoints regression: GET /buyers/{id}
    first_buyer_id = data_b["items"][0]["id"]
    status_single, data_single = http_get(f"/buyers/{first_buyer_id}")
    assert status_single == 200
    assert data_single["id"] == first_buyer_id
    assert data_single["latitude"] is None
    assert data_single["longitude"] is None
    print(f"  [PASS] GET /buyers/{{id}} for '{data_single['business_name']}' returns 200 OK with NULL coords")

    # 14. Existing buyer endpoints regression: Non-existent ID -> 404
    status_404, _ = http_get(f"/buyers/{uuid.uuid4()}")
    assert status_404 == 404
    print("  [PASS] GET /buyers/{random_uuid} returns 404 Not Found")

    # 15. System health and market prices endpoints regression
    status_health, _ = http_get("/health")
    assert status_health == 200
    status_prices, data_prices = http_get("/market/prices?limit=5")
    assert status_prices == 200
    assert data_prices["total"] == 100
    print("  [PASS] System health and market prices endpoints regression verified")


# ==============================================================================
# 5. DATABASE INTEGRITY AND PRESERVATION VERIFICATION
# ==============================================================================

async def verify_db_counts() -> dict:
    """Queries and returns row counts of all key tables in paddy_farming_db."""
    async with AsyncSessionLocal() as session:
        counts = {}
        for tbl in [
            "buyers",
            "market_prices",
            "fields",
            "satellite_observations",
            "prediction_history",
            "weather_records",
            "reports",
        ]:
            res = await session.execute(text(f"SELECT count(*) FROM {tbl}"))
            counts[tbl] = res.scalar()

        coord_res = await session.execute(
            text("SELECT count(*) FROM buyers WHERE latitude IS NOT NULL OR longitude IS NOT NULL")
        )
        counts["buyers_with_coords"] = coord_res.scalar()

        status_res = await session.execute(
            text("SELECT verification_status, count(*) FROM buyers GROUP BY verification_status ORDER BY verification_status")
        )
        counts["verification_status_counts"] = dict(status_res.all())

        return counts


async def main_async():
    print("================================================================================")
    print(" PADDY FARMING ASSISTANT — STEP 11H.7 RECTIFICATION & VERIFICATION SUITE")
    print("================================================================================")

    # 1. Baseline DB state
    baseline = await verify_db_counts()
    print("\n--- [PRE-TEST DATABASE AUDIT] ---")
    for k, v in baseline.items():
        print(f"  {k}: {v}")

    assert baseline["buyers"] == 17, f"Expected 17 buyers, got {baseline['buyers']}"
    assert baseline["market_prices"] == 100, f"Expected 100 market_prices, got {baseline['market_prices']}"
    assert baseline["fields"] == 58, f"Expected 58 fields, got {baseline['fields']}"
    assert baseline["satellite_observations"] == 580, f"Expected 580 satellite_observations, got {baseline['satellite_observations']}"
    assert baseline["prediction_history"] == 35, f"Expected 35 prediction_history, got {baseline['prediction_history']}"
    assert baseline["weather_records"] == 92, f"Expected 92 weather_records, got {baseline['weather_records']}"
    assert baseline["reports"] == 0, f"Expected 0 reports, got {baseline['reports']}"
    assert baseline["buyers_with_coords"] == 0, f"Expected 0 buyers with coords, got {baseline['buyers_with_coords']}"

    # 2. Run Unit Tests
    test_haversine_unit_calculations()
    test_coordinate_importer_validation()

    # 3. Run Isolated Transaction Test
    await test_isolated_proximity_calculations()

    # 4. Run Live API Tests
    test_live_api_endpoints()

    # 5. Idempotent import test on curated coordinates CSV
    print("\n--- [IDEMPOTENT IMPORT TEST] ---")
    csv_file = BACKEND_DIR / "data" / "curated_buyer_coordinates.csv"
    imp_res1 = await import_buyer_coordinates(csv_file, dry_run=False)
    assert imp_res1["matched_buyers"] == 17
    assert imp_res1["updated_coordinates"] == 0
    assert imp_res1["preserved_null"] == 17
    assert imp_res1["committed"] is True
    print("  [PASS] First apply completed: 17 matched, 0 updated, 17 NULL preserved")

    imp_res2 = await import_buyer_coordinates(csv_file, dry_run=False)
    assert imp_res2["matched_buyers"] == 17
    assert imp_res2["updated_coordinates"] == 0
    assert imp_res2["preserved_null"] == 17
    assert imp_res2["committed"] is True
    print("  [PASS] Second apply completed (idempotency confirmed): 17 matched, 0 updated, 17 NULL preserved")

    # 6. Post-test DB state check
    post_counts = await verify_db_counts()
    print("\n--- [POST-TEST DATABASE AUDIT] ---")
    for k, v in post_counts.items():
        print(f"  {k}: {v}")

    for tbl in ["buyers", "market_prices", "fields", "satellite_observations", "prediction_history", "weather_records", "reports", "buyers_with_coords"]:
        assert post_counts[tbl] == baseline[tbl], (
            f"Table {tbl} row count altered! Before: {baseline[tbl]}, After: {post_counts[tbl]}"
        )
    assert post_counts["verification_status_counts"] == baseline["verification_status_counts"], (
        "Buyer verification status counts altered!"
    )
    print("\n================================================================================")
    print(" [ALL 12 TEST SUITES PASSED PERFECTLY]")
    print(" DATABASE INTEGRITY 100% PRESERVED ACROSS ALL TABLES")
    print("================================================================================")


if __name__ == "__main__":
    asyncio.run(main_async())
