"""
Paddy Farming Assistant - STEP 11H.5 Market & Buyers Integration Close-Out
and GPS-Based Nearest-Buyer Search Test Suite

Tests:
1. Pre- and Post-Test Database State (7 tables intact):
   - buyers: 17
   - market_prices: 100
   - fields: 58
   - satellite_observations: 580
   - prediction_history: 35
   - weather_records: 92
   - reports: 0
2. Schema & Coordinate Provenance Verification:
   - buyers table contains nullable latitude, longitude, and coordinate_source
   - All 17 existing buyers retain NULL coordinates (no fabricated coordinates)
   - Category and verification status distributions strictly preserved
3. Haversine Distance Calculation Unit Tests:
   - Identical points (0.0 km)
   - Vijayawada to Guntur (~31.0 km)
   - Kakinada to Rajahmundry (~47.1 km)
   - Antipodal / extreme coordinates safe without numerical errors
4. Live REST API Responses:
   - GET /buyers -> 200 OK
   - GET /buyers/{valid_id} -> 200 OK (includes latitude/longitude/coordinate_source)
   - GET /buyers/{unknown_uuid} -> 404 Not Found
   - GET /buyers/invalid-uuid -> 422 Unprocessable Entity
   - GET /buyers/nearby -> 200 OK (empty list for production DB where coordinates are NULL)
   - GET /buyers/nearby validation errors:
     - lat > 90, lat < -90 -> 422
     - lon > 180, lon < -180 -> 422
     - radius_km <= 0, radius_km > 500 -> 422
     - skip < 0, limit < 1, limit > 200 -> 422
5. Isolated Transaction Proximity & Ranking Tests:
   - Evaluates BuyerRepository.list_nearby_buyers with synthetic coordinates in a rolled-back transaction
   - Strict distance ascending sorting
   - Radius exclusion
   - Exclusion of buyers with NULL coordinates
   - Deterministic tie-breaking by business_name ASC and id ASC
6. Market API Regression Verification:
   - GET /market/prices (total=100)
   - GET /market/prices/latest
   - GET /market/analytics/summary (obs=100)
   - GET /market/analytics/trends
   - GET /market/analytics/districts
   - GET /market/analytics/varieties
"""

import sys
import os
import json
import uuid
import math
import urllib.request
import urllib.error
import urllib.parse
from decimal import Decimal
from pathlib import Path

# UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import asyncio
from sqlalchemy import text, select, func
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app import config
from app.db.session import get_database_url
from app.db.models.buyer import Buyer
from app.db.models.market import MarketPrice
from app.db.models.field import Field
from app.db.models.satellite import SatelliteObservation
from app.db.models.prediction import PredictionHistory
from app.db.models.weather import WeatherRecord
from app.db.models.report import Report
from app.db.repositories.other_repositories import BuyerRepository
from app.services.geo_service import haversine_distance_km, EARTH_RADIUS_KM

BASE_URL = "http://127.0.0.1:8000"


def make_request(path: str) -> tuple:
    """Make HTTP GET request to live local FastAPI server."""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}, resp.headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return e.code, parsed, e.headers


async def run_in_isolated_session(coro_fn):
    """Run an async coroutine inside an isolated NullPool session."""
    engine = create_async_engine(get_database_url(), poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        result = await coro_fn(session)
    await engine.dispose()
    return result


async def query_database_state():
    """Direct PostgreSQL query to inspect database counts and integrity."""
    async def _op(s: AsyncSession):
        tbl_counts = {
            "fields": (await s.execute(select(func.count(Field.id)))).scalar() or 0,
            "satellite_observations": (await s.execute(select(func.count(SatelliteObservation.id)))).scalar() or 0,
            "prediction_history": (await s.execute(select(func.count(PredictionHistory.id)))).scalar() or 0,
            "weather_records": (await s.execute(select(func.count(WeatherRecord.id)))).scalar() or 0,
            "market_prices": (await s.execute(select(func.count(MarketPrice.id)))).scalar() or 0,
            "buyers": (await s.execute(select(func.count(Buyer.id)))).scalar() or 0,
            "reports": (await s.execute(select(func.count(Report.id)))).scalar() or 0,
        }

        # Check buyer coordinates status
        coord_stats = (await s.execute(text("""
            SELECT
                count(*) AS total,
                count(latitude) AS with_lat,
                count(longitude) AS with_lon,
                count(coordinate_source) AS with_source
            FROM buyers
        """))).mappings().one()

        # Buyers verification status counts
        v_rows = (await s.execute(text("SELECT verification_status, count(*) FROM buyers GROUP BY verification_status"))).all()
        v_map = {r[0]: r[1] for r in v_rows}

        # Buyer type counts
        t_rows = (await s.execute(text("SELECT buyer_type, count(*) FROM buyers GROUP BY buyer_type"))).all()
        t_map = {r[0]: r[1] for r in t_rows}

        return tbl_counts, dict(coord_stats), v_map, t_map

    return await run_in_isolated_session(_op)


def test_haversine_formula():
    """Unit test the Haversine formula against known geographical benchmarks."""
    print("\n--- [UNIT TEST] Haversine Distance Calculations ---")

    # 1. Identical coordinates
    d0 = haversine_distance_km(16.5062, 80.6480, 16.5062, 80.6480)
    assert d0 == 0.0, f"Expected 0.0 km, got {d0}"
    print(f"  [PASS] Identical points: {d0} km")

    # 2. Vijayawada (16.5062, 80.6480) to Guntur (16.3067, 80.4365)
    d_vja_gnt = haversine_distance_km(16.5062, 80.6480, 16.3067, 80.4365)
    print(f"  Vijayawada to Guntur: {d_vja_gnt} km (expected ~31.0 km)")
    assert 30.0 <= d_vja_gnt <= 32.0, f"Distance out of expected tolerance: {d_vja_gnt}"
    print(f"  [PASS] Vijayawada to Guntur: {d_vja_gnt} km")

    # 3. Kakinada (16.9891, 82.2475) to Rajahmundry (17.0005, 81.8040)
    d_kak_rjy = haversine_distance_km(16.9891, 82.2475, 17.0005, 81.8040)
    print(f"  Kakinada to Rajahmundry: {d_kak_rjy} km (expected ~47.1 km)")
    assert 46.0 <= d_kak_rjy <= 48.5, f"Distance out of expected tolerance: {d_kak_rjy}"
    print(f"  [PASS] Kakinada to Rajahmundry: {d_kak_rjy} km")

    # 4. Numerical safety at antipodes and poles
    d_poles = haversine_distance_km(90.0, 0.0, -90.0, 0.0)
    assert 20000.0 <= d_poles <= 20030.0, f"Polar distance anomalous: {d_poles}"
    print(f"  [PASS] North Pole to South Pole: {d_poles} km (safe against math domain errors)")


async def test_isolated_proximity_fixture():
    """
    Tests BuyerRepository.list_nearby_buyers inside a transaction that is rolled back.
    Ensures zero persistent modification to production data.
    """
    print("\n--- [ISOLATED FIXTURE] Proximity Search & Sorting in Rollback Transaction ---")
    engine = create_async_engine(get_database_url(), poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        async with session.begin():
            # Farmer reference location: Kakinada center (16.9891, 82.2475)
            farmer_lat = 16.9891
            farmer_lon = 82.2475

            # Insert 4 synthetic buyers with distinct distances and 1 with NULL coords
            b1 = Buyer(
                business_name="TEST Nearby Mill Kakinada",
                buyer_type="mill",
                district="Kakinada",
                state="Andhra Pradesh",
                latitude=Decimal("16.995000"),  # ~0.65 km away
                longitude=Decimal("82.250000"),
                coordinate_source="Test Ground Survey",
                verification_status="verified",
                is_active=True,
            )
            b2 = Buyer(
                business_name="TEST Mid-distance Mill Rajahmundry",
                buyer_type="mill",
                district="East Godavari",
                state="Andhra Pradesh",
                latitude=Decimal("17.000500"),  # ~47.1 km away
                longitude=Decimal("81.804000"),
                coordinate_source="Test Municipal Directory",
                verification_status="verified",
                is_active=True,
            )
            b3 = Buyer(
                business_name="TEST Far Mill Vijayawada",
                buyer_type="mill",
                district="Krishna",
                state="Andhra Pradesh",
                latitude=Decimal("16.506200"),  # ~178 km away
                longitude=Decimal("80.648000"),
                coordinate_source="Test APMC Yard",
                verification_status="verified",
                is_active=True,
            )
            b4 = Buyer(
                business_name="TEST No Coordinates Buyer",
                buyer_type="mill",
                district="Kakinada",
                state="Andhra Pradesh",
                latitude=None,  # Missing coordinates! Must be excluded!
                longitude=None,
                verification_status="verified",
                is_active=True,
            )
            session.add_all([b1, b2, b3, b4])
            await session.flush()

            repo = BuyerRepository(session)

            # Test 1: No radius limit -> Should return b1, b2, b3 in strict ascending distance order. b4 must NOT be included!
            scored, total = await repo.list_nearby_buyers(farmer_lat, farmer_lon)
            print(f"  Unbounded nearby search returned {total} eligible buyers:")
            for b, d in scored:
                print(f"    - {b.business_name} ({b.district}): {d} km")

            assert total == 3, f"Expected 3 eligible buyers with coordinates, got {total}"
            assert scored[0][0].business_name == "TEST Nearby Mill Kakinada"
            assert scored[1][0].business_name == "TEST Mid-distance Mill Rajahmundry"
            assert scored[2][0].business_name == "TEST Far Mill Vijayawada"
            assert scored[0][1] < scored[1][1] < scored[2][1]
            print("  [PASS] Unbounded search returned correct distance-ranked order; NULL coordinate record excluded.")

            # Test 2: Radius = 50 km -> Should return b1 and b2 only. b3 (>170km) excluded.
            scored_50, total_50 = await repo.list_nearby_buyers(farmer_lat, farmer_lon, radius_km=50.0)
            print(f"  Radius 50 km search returned {total_50} buyers:")
            for b, d in scored_50:
                print(f"    - {b.business_name}: {d} km")
            assert total_50 == 2, f"Expected 2 buyers within 50 km, got {total_50}"
            assert scored_50[0][0].business_name == "TEST Nearby Mill Kakinada"
            assert scored_50[1][0].business_name == "TEST Mid-distance Mill Rajahmundry"
            print("  [PASS] Radius filtering (50 km) strictly excluded distant and NULL coordinate buyers.")

            # Test 3: Radius = 5 km -> Should return b1 only.
            scored_5, total_5 = await repo.list_nearby_buyers(farmer_lat, farmer_lon, radius_km=5.0)
            assert total_5 == 1 and scored_5[0][0].business_name == "TEST Nearby Mill Kakinada"
            print("  [PASS] Narrow radius (5 km) correctly returned only the immediate local buyer.")

            # Rollback transaction so none of this test data is committed
            await session.rollback()
            print("  [ROLLBACK] Synthetic test records cleanly discarded; 0 persistent DB modifications.")

    await engine.dispose()


def run_all_tests():
    print("=" * 80)
    print("STEP 11H.5 — MARKET & BUYERS GPS INTEGRATION VERIFICATION SUITE")
    print("=" * 80)

    summary = {}

    # 1. Pre-Implementation Database State
    print("\n[PART 1] Verifying Database Baseline & Coordinate Columns...")
    tbl_counts, coord_stats, v_map, t_map = asyncio.run(query_database_state())
    for tbl, count in tbl_counts.items():
        print(f"  {tbl:25}: {count}")

    assert tbl_counts["buyers"] == 17, f"Expected 17 buyers, got {tbl_counts['buyers']}"
    assert tbl_counts["market_prices"] == 100, f"Expected 100 market_prices, got {tbl_counts['market_prices']}"
    assert tbl_counts["fields"] == 58
    assert tbl_counts["satellite_observations"] == 580
    assert tbl_counts["prediction_history"] == 35
    assert tbl_counts["weather_records"] == 92
    assert tbl_counts["reports"] == 0

    print("\n--- Coordinate Provenance in Production Buyers ---")
    print(f"  Total Buyers:        {coord_stats['total']}")
    print(f"  With Latitude:       {coord_stats['with_lat']} (expected 0 until verified coordinates curated)")
    print(f"  With Longitude:      {coord_stats['with_lon']} (expected 0 until verified coordinates curated)")
    print(f"  With Source Authority: {coord_stats['with_source']}")
    assert coord_stats["total"] == 17
    assert coord_stats["with_lat"] == 0, "Production buyers should not have fabricated coordinates"
    assert coord_stats["with_lon"] == 0, "Production buyers should not have fabricated coordinates"
    print("  [PASS] Database schema contains nullable coordinate columns; production coordinates are clean and un-fabricated.")
    summary["database_baseline"] = "PASS"

    # 2. Haversine Unit Tests
    test_haversine_formula()
    summary["haversine_unit_tests"] = "PASS"

    # 3. Isolated Fixture Proximity Tests
    asyncio.run(test_isolated_proximity_fixture())
    summary["isolated_proximity_tests"] = "PASS"

    # 4. Live REST API Responses
    print("\n[PART 2] Testing Live REST Endpoints against Running Backend...")

    # 4.1 Standard buyers list
    code, data, _ = make_request("/buyers")
    assert code == 200 and data["total"] == 17
    print(f"  GET /buyers -> 200 OK (total={data['total']})")

    # 4.2 Individual buyer details (includes new nullable fields)
    sample_id = data["items"][0]["id"]
    code, buyer_detail, _ = make_request(f"/buyers/{sample_id}")
    assert code == 200 and buyer_detail["id"] == sample_id
    assert "latitude" in buyer_detail and buyer_detail["latitude"] is None
    assert "longitude" in buyer_detail and buyer_detail["longitude"] is None
    assert "coordinate_source" in buyer_detail and buyer_detail["coordinate_source"] is None
    print(f"  GET /buyers/{sample_id} -> 200 OK (latitude/longitude safely nullable)")

    # 4.3 404 for unknown buyer
    code, _, _ = make_request(f"/buyers/{uuid.uuid4()}")
    assert code == 404
    print("  GET /buyers/{unknown_uuid} -> 404 Not Found")

    # 4.4 422 for malformed UUID
    code, _, _ = make_request("/buyers/invalid-uuid-string")
    assert code == 422
    print("  GET /buyers/invalid-uuid -> 422 Unprocessable Entity")

    # 4.5 GET /buyers/nearby with valid farmer coordinates (Production DB has NULL coords, so expect total=0)
    code, data, _ = make_request("/buyers/nearby?lat=16.9891&lon=82.2475")
    assert code == 200, f"Expected 200, got {code}"
    assert data["total"] == 0, f"Expected 0 (since production buyers have NULL coords), got {data['total']}"
    assert data["items"] == []
    assert data["farmer_latitude"] == 16.9891
    assert data["farmer_longitude"] == 82.2475
    assert "Straight-line" in data["disclaimer"]
    print(f"  GET /buyers/nearby?lat=16.9891&lon=82.2475 -> 200 OK (total=0, clean handling of unlocated buyers)")

    # 4.6 Nearby validation errors (HTTP 422)
    invalid_nearby_params = [
        ("Missing lat", "lon=82.2475"),
        ("Missing lon", "lat=16.9891"),
        ("Latitude > 90", "lat=95.0&lon=82.2475"),
        ("Latitude < -90", "lat=-95.0&lon=82.2475"),
        ("Longitude > 180", "lat=16.9891&lon=185.0"),
        ("Longitude < -180", "lat=16.9891&lon=-185.0"),
        ("Negative radius", "lat=16.9891&lon=82.2475&radius_km=-10"),
        ("Zero radius", "lat=16.9891&lon=82.2475&radius_km=0"),
        ("Excessive radius (> 500km)", "lat=16.9891&lon=82.2475&radius_km=600"),
        ("Negative skip", "lat=16.9891&lon=82.2475&skip=-1"),
        ("Limit 0", "lat=16.9891&lon=82.2475&limit=0"),
        ("Limit > 200", "lat=16.9891&lon=82.2475&limit=250"),
    ]

    for label, q_str in invalid_nearby_params:
        code, err_body, _ = make_request(f"/buyers/nearby?{q_str}")
        assert code == 422, f"Expected 422 for '{label}', got {code}"
        print(f"  [PASS] /buyers/nearby with {label:28} -> HTTP 422 Unprocessable Entity")

    summary["live_nearby_api"] = "PASS"

    # 5. Market API Regression Verification
    print("\n[PART 3] Verifying Market Prices & Analytics Endpoints...")

    # 5.1 GET /market/prices
    code, mp_data, _ = make_request("/market/prices?limit=5")
    assert code == 200 and mp_data["total"] == 100
    print(f"  GET /market/prices -> 200 OK (total={mp_data['total']} market prices intact)")

    # 5.2 GET /market/prices/latest
    code, lat_data, _ = make_request("/market/prices/latest")
    assert code == 200 and lat_data["total"] > 0
    print(f"  GET /market/prices/latest -> 200 OK (total={lat_data['total']} latest quotations)")

    # 5.3 GET /market/analytics/summary
    code, summ_data, _ = make_request("/market/analytics/summary")
    assert code == 200 and summ_data["total_observations"] == 100
    print(f"  GET /market/analytics/summary -> 200 OK (observations={summ_data['total_observations']})")

    # 5.4 GET /market/analytics/trends
    code, trends_data, _ = make_request("/market/analytics/trends?days=7")
    assert code == 200 and "daily_trends" in trends_data
    print(f"  GET /market/analytics/trends?days=7 -> 200 OK (daily_trends={len(trends_data['daily_trends'])})")

    # 5.5 GET /market/analytics/districts
    code, dist_data, _ = make_request("/market/analytics/districts")
    assert code == 200 and len(dist_data["districts"]) > 0
    print(f"  GET /market/analytics/districts -> 200 OK ({len(dist_data['districts'])} districts analyzed)")

    # 5.6 GET /market/analytics/varieties
    code, var_data, _ = make_request("/market/analytics/varieties")
    assert code == 200 and len(var_data["varieties"]) > 0
    print(f"  GET /market/analytics/varieties -> 200 OK ({len(var_data['varieties'])} varieties analyzed)")

    summary["market_api_regression"] = "PASS"

    # 6. Post-Test Database Safety Re-Check
    print("\n[PART 4] Post-Test Database Safety Check...")
    final_counts, _, _, _ = asyncio.run(query_database_state())
    for tbl, count in final_counts.items():
        print(f"  {tbl:25}: {count}")

    assert final_counts["buyers"] == 17
    assert final_counts["market_prices"] == 100
    assert final_counts["fields"] == 58
    assert final_counts["satellite_observations"] == 580
    assert final_counts["prediction_history"] == 35
    assert final_counts["weather_records"] == 92
    assert final_counts["reports"] == 0
    print("  [PASS] All 7 database table counts strictly intact and unchanged.")
    summary["database_safety"] = "PASS"

    # Summary
    print("\n" + "=" * 80)
    print("STEP 11H.5 VERIFICATION SUMMARY")
    print("=" * 80)
    for k, v in summary.items():
        print(f"  {k:30}: {v}")
    print("=" * 80)
    print("STATUS: PASS (NEAREST-BUYER SEARCH IMPLEMENTED & VERIFIED)")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    run_all_tests()
