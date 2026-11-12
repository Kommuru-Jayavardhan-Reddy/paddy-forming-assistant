"""
Paddy Farming Assistant - STEP 11H.3 Buyer Data Ingestion Verification Suite
Tests:
1. PostgreSQL Database Row Counts & Integrity:
   - buyers == 17
   - market_prices == 100 (intact genuine Data.gov.in quotes)
   - fields == 58
   - satellite_observations == 580
   - prediction_history == 35
   - weather_records == 92
   - reports == 0
2. Category and Status Constraints:
   - verified == 15
   - pending == 2
   - unverified == 0
   - government_agency == 5, mill == 6, fpo == 4, trader == 2
   - zero duplicate (business_name, district) pairs
3. Importer Idempotency:
   - Re-importing curated_verified_buyers.csv produces 0 extra rows (count remains 17)
4. REST API Endpoints Verification:
   - GET /buyers -> 200 OK (total=17)
   - GET /buyers?district=Kakinada -> 200 OK (total=3)
   - GET /buyers?buyer_type=fpo -> 200 OK (total=4)
   - GET /buyers?buyer_type=government_agency -> 200 OK (total=5)
   - GET /buyers?buyer_type=mill -> 200 OK (total=6)
   - GET /buyers?buyer_type=trader -> 200 OK (total=2)
   - GET /buyers?verification_status=verified -> 200 OK (total=15)
   - GET /buyers?verification_status=pending -> 200 OK (total=2)
   - GET /buyers/{buyer_id} -> 200 OK (full profile)
   - GET /buyers/{unknown_uuid} -> 404 Not Found
   - GET /buyers/invalid-uuid -> 422 Unprocessable Entity
5. Existing Endpoints Regression:
   - GET /health -> 200 OK
   - GET /market/prices -> 200 OK (total=100)
   - GET /market/analytics/summary -> 200 OK (total_observations=100)
"""

import sys
import os
import json
import uuid
import urllib.request
import urllib.error
from pathlib import Path

# UTF-8 output on Windows
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


def make_request(path: str) -> tuple:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return e.code, parsed


async def run_in_isolated_session(coro_fn):
    engine = create_async_engine(get_database_url(), poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        result = await coro_fn(session)
    await engine.dispose()
    return result


async def get_all_table_counts():
    async def _op(s):
        f = (await s.execute(select(func.count(Field.id)))).scalar() or 0
        sat = (await s.execute(select(func.count(SatelliteObservation.id)))).scalar() or 0
        pred = (await s.execute(select(func.count(PredictionHistory.id)))).scalar() or 0
        w = (await s.execute(select(func.count(WeatherRecord.id)))).scalar() or 0
        mp = (await s.execute(select(func.count(MarketPrice.id)))).scalar() or 0
        b = (await s.execute(select(func.count(Buyer.id)))).scalar() or 0
        rep = (await s.execute(select(func.count(Report.id)))).scalar() or 0
        return {
            "fields": f,
            "satellite_observations": sat,
            "prediction_history": pred,
            "weather_records": w,
            "market_prices": mp,
            "buyers": b,
            "reports": rep,
        }
    return await run_in_isolated_session(_op)


async def verify_buyer_aggregates():
    async def _op(s):
        # Verification status counts
        v_rows = (await s.execute(text("SELECT verification_status, count(*) FROM buyers GROUP BY verification_status"))).all()
        v_map = {r[0]: r[1] for r in v_rows}

        # Buyer type counts
        t_rows = (await s.execute(text("SELECT buyer_type, count(*) FROM buyers GROUP BY buyer_type"))).all()
        t_map = {r[0]: r[1] for r in t_rows}

        # Duplicate check
        dup_cnt = (await s.execute(text("SELECT count(*) - count(DISTINCT (lower(business_name), lower(district))) FROM buyers"))).scalar() or 0

        # Sample buyer ID
        first_buyer = (await s.execute(select(Buyer).order_by(Buyer.business_name).limit(1))).scalar_one_or_none()

        return v_map, t_map, dup_cnt, str(first_buyer.id) if first_buyer else None
    return await run_in_isolated_session(_op)


def run_verification():
    print("=" * 80)
    print("STEP 11H.3 — CONTROLLED BUYER DATA INGESTION VERIFICATION")
    print("=" * 80)

    results = {}

    # 1. Database Table Counts
    print("\n[CHECK 1] Verifying Database Table Counts...")
    counts = asyncio.run(get_all_table_counts())
    for tbl, cnt in counts.items():
        print(f"  {tbl}: {cnt}")

    assert counts["buyers"] == 17, f"Expected 17 buyers, got {counts['buyers']}"
    assert counts["market_prices"] == 100, f"Expected 100 market_prices, got {counts['market_prices']}"
    assert counts["fields"] == 58, f"Fields altered: {counts['fields']}"
    assert counts["satellite_observations"] == 580, f"Satellite altered: {counts['satellite_observations']}"
    assert counts["prediction_history"] == 35, f"Predictions altered: {counts['prediction_history']}"
    assert counts["weather_records"] == 92, f"Weather altered: {counts['weather_records']}"
    assert counts["reports"] == 0, f"Reports altered: {counts['reports']}"
    print("  [PASS] All 7 tables match expected post-import row counts.")
    results["check_1_table_counts"] = "PASS"

    # 2. Buyer Aggregates & Deduplication
    print("\n[CHECK 2] Verifying Buyer Verification Status & Type Distribution...")
    v_map, t_map, dup_cnt, sample_id = asyncio.run(verify_buyer_aggregates())
    print(f"  Verification Statuses: {v_map}")
    print(f"  Buyer Types:           {t_map}")
    print(f"  Duplicate Count:       {dup_cnt}")

    assert v_map.get("verified") == 15, f"Expected 15 verified, got {v_map.get('verified')}"
    assert v_map.get("pending") == 2, f"Expected 2 pending, got {v_map.get('pending')}"
    assert v_map.get("unverified", 0) == 0, f"Expected 0 unverified, got {v_map.get('unverified')}"
    assert t_map.get("government_agency") == 5, f"Expected 5 government_agency, got {t_map.get('government_agency')}"
    assert t_map.get("mill") == 6, f"Expected 6 mill, got {t_map.get('mill')}"
    assert t_map.get("fpo") == 4, f"Expected 4 fpo, got {t_map.get('fpo')}"
    assert t_map.get("trader") == 2, f"Expected 2 trader, got {t_map.get('trader')}"
    assert dup_cnt == 0, f"Duplicates detected: {dup_cnt}"
    print("  [PASS] Verification status preserved; 0 duplicates detected.")
    results["check_2_aggregates_and_duplicates"] = "PASS"

    # 3. Importer Idempotency Verification
    print("\n[CHECK 3] Verifying Importer Idempotency...")
    from scripts.import_market_buyer_csv import import_buyers
    csv_path = BACKEND_DIR / "data" / "curated_verified_buyers.csv"
    imported_cnt = asyncio.run(import_buyers(csv_path, dry_run=False))
    print(f"  Re-import run processed {imported_cnt} records.")

    post_counts = asyncio.run(get_all_table_counts())
    assert post_counts["buyers"] == 17, f"Idempotency failed: count grew to {post_counts['buyers']}"
    print(f"  Post-re-import buyers count: {post_counts['buyers']} (strictly preserved at 17).")
    print("  [PASS] Importer confirmed 100% idempotent.")
    results["check_3_idempotency"] = "PASS"

    # 4. REST API Endpoint Verification
    print("\n[CHECK 4] Verifying Buyer REST Endpoints against Live Backend...")

    # 4.1 All buyers
    st, res = make_request("/buyers")
    assert st == 200 and res["total"] == 17 and len(res["items"]) == 17
    print(f"  GET /buyers -> 200 OK (total={res['total']})")

    # 4.2 District filter (Kakinada)
    st, res = make_request("/buyers?district=Kakinada")
    assert st == 200 and res["total"] == 3
    print(f"  GET /buyers?district=Kakinada -> 200 OK (total={res['total']})")

    # 4.3 Category filter (fpo)
    st, res = make_request("/buyers?buyer_type=fpo")
    assert st == 200 and res["total"] == 4
    print(f"  GET /buyers?buyer_type=fpo -> 200 OK (total={res['total']})")

    # 4.4 Category filter (government_agency)
    st, res = make_request("/buyers?buyer_type=government_agency")
    assert st == 200 and res["total"] == 5
    print(f"  GET /buyers?buyer_type=government_agency -> 200 OK (total={res['total']})")

    # 4.5 Category filter (mill)
    st, res = make_request("/buyers?buyer_type=mill")
    assert st == 200 and res["total"] == 6
    print(f"  GET /buyers?buyer_type=mill -> 200 OK (total={res['total']})")

    # 4.6 Category filter (trader)
    st, res = make_request("/buyers?buyer_type=trader")
    assert st == 200 and res["total"] == 2
    print(f"  GET /buyers?buyer_type=trader -> 200 OK (total={res['total']})")

    # 4.7 Status filter (verified)
    st, res = make_request("/buyers?verification_status=verified")
    assert st == 200 and res["total"] == 15
    print(f"  GET /buyers?verification_status=verified -> 200 OK (total={res['total']})")

    # 4.8 Status filter (pending)
    st, res = make_request("/buyers?verification_status=pending")
    assert st == 200 and res["total"] == 2
    print(f"  GET /buyers?verification_status=pending -> 200 OK (total={res['total']})")

    # 4.9 Combined filter (district=SPSR Nellore & verification_status=verified)
    st, res = make_request("/buyers?district=SPSR%20Nellore&verification_status=verified")
    assert st == 200 and res["total"] == 2
    print(f"  GET /buyers?district=SPSR Nellore&status=verified -> 200 OK (total={res['total']})")

    # 4.10 Single buyer profile
    st, res = make_request(f"/buyers/{sample_id}")
    assert st == 200 and res["id"] == sample_id
    assert res["business_name"] is not None
    assert isinstance(res["preferred_varieties"], list)
    print(f"  GET /buyers/{sample_id} -> 200 OK ({res['business_name']})")

    # 4.11 404 for unknown buyer
    st, res = make_request(f"/buyers/{uuid.uuid4()}")
    assert st == 404
    print("  GET /buyers/{unknown_uuid} -> 404 Not Found")

    # 4.12 422 for malformed UUID
    st, res = make_request("/buyers/invalid-uuid")
    assert st == 422
    print("  GET /buyers/invalid-uuid -> 422 Unprocessable Entity")

    print("  [PASS] All buyer REST endpoints return genuine, verified responses.")
    results["check_4_rest_endpoints"] = "PASS"

    # 5. Regression Check on Unrelated Endpoints
    print("\n[CHECK 5] Regression Checking Other Endpoints...")
    st, res = make_request("/health")
    assert st == 200 and res["status"] == "healthy"
    print(f"  GET /health -> 200 OK: {res}")

    st, res = make_request("/market/prices?limit=5")
    assert st == 200 and res["total"] == 100
    print(f"  GET /market/prices -> 200 OK (total={res['total']} market prices intact)")

    st, res = make_request("/market/analytics/summary")
    assert st == 200 and res["total_observations"] == 100
    print(f"  GET /market/analytics/summary -> 200 OK (obs={res['total_observations']} intact)")

    print("  [PASS] Non-buyer endpoints and market prices remain 100% regression-free.")
    results["check_5_regression"] = "PASS"

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"ALL STEP 11H.3 VERIFICATIONS PASSED ({len(results)}/{len(results)}) (100% PASS)")
    print("STATUS: PASS (CONTROLLED INGESTION COMPLETE)")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_verification()
