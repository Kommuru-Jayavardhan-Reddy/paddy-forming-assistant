"""
Paddy Farming Assistant - STEP 11H.6 Buyer Coordinate Curation & Validation Suite

Verifies:
1. Curation CSV Structure & Integrity:
   - File exists at backend/data/curated_buyer_coordinates.csv
   - Header matches expected columns
   - Exactly 17 records correspond 1:1 with authentic database buyers
   - No fabricated coordinates present (accepted == 0, rejected == 5, unresolved == 12)
   - Source reference and evidence notes present for every row
2. Database Safety:
   - Production PostgreSQL database was NOT automatically modified
   - All 17 buyers in database retain latitude IS NULL and longitude IS NULL
   - All 100 market_prices remain intact
   - fields (58), satellite (580), prediction (35), weather (92), reports (0) untouched
3. Live API Stability:
   - GET /buyers -> 200 OK (total=17)
   - GET /buyers/nearby -> 200 OK (total=0, items=[], clean handling of unlocated buyers)
   - GET /market/prices -> 200 OK (total=100)
"""

import sys
import os
import csv
import json
import urllib.request
import urllib.error
from decimal import Decimal, InvalidOperation
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

BASE_URL = "http://127.0.0.1:8000"
CSV_PATH = BACKEND_DIR / "data" / "curated_buyer_coordinates.csv"

EXPECTED_COLUMNS = [
    "business_name",
    "district",
    "latitude",
    "longitude",
    "coordinate_source",
    "source_reference",
    "evidence_notes",
    "coordinate_verification_status",
]


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


async def query_db_state():
    """Query PostgreSQL directly via NullPool session."""
    engine = create_async_engine(get_database_url(), poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        tbl_counts = {
            "fields": (await session.execute(select(func.count(Field.id)))).scalar() or 0,
            "satellite_observations": (await session.execute(select(func.count(SatelliteObservation.id)))).scalar() or 0,
            "prediction_history": (await session.execute(select(func.count(PredictionHistory.id)))).scalar() or 0,
            "weather_records": (await session.execute(select(func.count(WeatherRecord.id)))).scalar() or 0,
            "market_prices": (await session.execute(select(func.count(MarketPrice.id)))).scalar() or 0,
            "buyers": (await session.execute(select(func.count(Buyer.id)))).scalar() or 0,
            "reports": (await session.execute(select(func.count(Report.id)))).scalar() or 0,
        }

        # Check production coordinates
        coord_counts = (await session.execute(text("""
            SELECT
                count(*) AS total,
                count(latitude) AS with_lat,
                count(longitude) AS with_lon
            FROM buyers
        """))).mappings().one()

        buyers_in_db = (await session.execute(select(Buyer.business_name, Buyer.district))).all()
        db_pairs = {(b[0].strip().lower(), b[1].strip().lower()) for b in buyers_in_db}

    await engine.dispose()
    return tbl_counts, dict(coord_counts), db_pairs


def run_curation_audit():
    print("=" * 80)
    print("STEP 11H.6 — BUYER COORDINATE CURATION & VALIDATION SUITE")
    print("=" * 80)

    summary = {}

    # 1. Inspect CSV File
    print("\n[PART 1] Inspecting curated_buyer_coordinates.csv...")
    assert CSV_PATH.exists(), f"Curation file not found: {CSV_PATH}"
    print(f"  File exists at: {CSV_PATH}")

    rows = []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == EXPECTED_COLUMNS, f"Invalid CSV header: {reader.fieldnames}"
        for line_num, r in enumerate(reader, start=2):
            rows.append(r)

    print(f"  Parsed {len(rows)} curation rows.")
    assert len(rows) == 17, f"Expected exactly 17 curation rows, got {len(rows)}"

    accepted = 0
    rejected = 0
    unresolved = 0

    for i, r in enumerate(rows, start=1):
        b_name = r["business_name"].strip()
        dist = r["district"].strip()
        lat_str = r["latitude"].strip()
        lon_str = r["longitude"].strip()
        status = r["coordinate_verification_status"].strip().lower()
        src = r["coordinate_source"].strip()
        ref = r["source_reference"].strip()
        notes = r["evidence_notes"].strip()

        assert b_name, f"Row {i}: Missing business_name"
        assert dist, f"Row {i}: Missing district"
        assert src, f"Row {i}: Missing coordinate_source"
        assert ref, f"Row {i}: Missing source_reference"
        assert notes, f"Row {i}: Missing evidence_notes"
        assert status in {"accepted", "rejected", "unresolved"}, f"Row {i}: Invalid status '{status}'"

        if status == "accepted":
            accepted += 1
            lat = Decimal(lat_str)
            lon = Decimal(lon_str)
            assert -90 <= lat <= 90, f"Row {i}: Invalid latitude {lat}"
            assert -180 <= lon <= 180, f"Row {i}: Invalid longitude {lon}"
        elif status == "rejected":
            rejected += 1
            assert not lat_str and not lon_str, f"Row {i}: Rejected row must have empty coordinates"
        elif status == "unresolved":
            unresolved += 1
            assert not lat_str and not lon_str, f"Row {i}: Unresolved row must have empty coordinates"

    print(f"  Coordinate Audit Breakdown:")
    print(f"    - Accepted (verified official coordinates):  {accepted}")
    print(f"    - Rejected (approximate/centroid discarded): {rejected}")
    print(f"    - Unresolved (no coordinates in registry):   {unresolved}")
    print(f"    - Total Buyers Reviewed:                     {len(rows)}")

    assert accepted == 0, f"Expected 0 accepted pairs (no official GIS coordinates published), got {accepted}"
    assert rejected == 5, f"Expected 5 rejected pairs (Collectorate compound approximations), got {rejected}"
    assert unresolved == 12, f"Expected 12 unresolved pairs, got {unresolved}"
    print("  [PASS] Curation file strictly follows zero-fabrication rules.")
    summary["curation_file_integrity"] = "PASS"

    # 2. Match with Production Database Buyers
    print("\n[PART 2] Cross-Referencing with PostgreSQL Production Buyers...")
    tbl_counts, coord_counts, db_pairs = asyncio.run(query_db_state())

    for r in rows:
        pair = (r["business_name"].strip().lower(), r["district"].strip().lower())
        assert pair in db_pairs, f"Curation record not in production DB: {r['business_name']} ({r['district']})"

    print(f"  All {len(rows)} curated records match existing production buyers 1-to-1.")
    summary["buyer_identity_match"] = "PASS"

    # 3. Database Safety Check (Zero Automated Modifications)
    print("\n[PART 3] Confirming Production Database Safety...")
    for tbl, count in tbl_counts.items():
        print(f"  {tbl:25}: {count}")

    assert tbl_counts["buyers"] == 17
    assert tbl_counts["market_prices"] == 100
    assert tbl_counts["fields"] == 58
    assert tbl_counts["satellite_observations"] == 580
    assert tbl_counts["prediction_history"] == 35
    assert tbl_counts["weather_records"] == 92
    assert tbl_counts["reports"] == 0

    print(f"  Production Buyer Coordinates in DB: with_lat={coord_counts['with_lat']}, with_lon={coord_counts['with_lon']}")
    assert coord_counts["with_lat"] == 0, "Production buyers must remain NULL (no auto-import)"
    assert coord_counts["with_lon"] == 0, "Production buyers must remain NULL (no auto-import)"
    print("  [PASS] Database remains strictly untouched; zero unverified coordinates imported.")
    summary["database_safety"] = "PASS"

    # 4. Live API Verification
    print("\n[PART 4] Live API Verification against Running Daemon...")
    code, b_data, _ = make_request("/buyers")
    assert code == 200 and b_data["total"] == 17
    print(f"  GET /buyers -> 200 OK (total={b_data['total']})")

    code, nearby_data, _ = make_request("/buyers/nearby?lat=16.9891&lon=82.2475")
    assert code == 200 and nearby_data["total"] == 0 and nearby_data["items"] == []
    print(f"  GET /buyers/nearby -> 200 OK (total=0, clean handling of unlocated buyers)")

    code, mp_data, _ = make_request("/market/prices?limit=5")
    assert code == 200 and mp_data["total"] == 100
    print(f"  GET /market/prices -> 200 OK (total={mp_data['total']} market prices intact)")

    summary["live_api_stability"] = "PASS"

    # Summary
    print("\n" + "=" * 80)
    print("STEP 11H.6 VERIFICATION SUMMARY")
    print("=" * 80)
    for k, v in summary.items():
        print(f"  {k:30}: {v}")
    print("=" * 80)
    print("FINAL STATUS: PASS WITH LIMITATIONS (NO OFFICIAL POINT-LEVEL GPS COORDINATES IN PRIMARY REGISTRIES)")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    run_curation_audit()
