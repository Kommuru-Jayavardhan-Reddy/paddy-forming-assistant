"""
Paddy Farming Assistant - STEP 11H.1 Buyer Functionality & Source Audit Verification Suite
Verifies:
1. Baseline database counts (buyers=0, market_prices=100, fields=58, satellite_observations=580).
2. Existing buyer REST API endpoints on empty database:
   - GET /buyers -> 200 OK, items=[], total=0
   - GET /buyers?district=Chittoor -> 200 OK, items=[], total=0
   - GET /buyers?buyer_type=mill -> 200 OK, items=[], total=0
   - GET /buyers/{unknown_uuid} -> 404 Not Found
   - GET /buyers/not-a-uuid -> 422 Unprocessable Entity
3. Isolated test buyer seeding & filtering verification:
   - Seeding 2 isolated test buyers with prefix 'TEST_'
   - GET /buyers with district filter
   - GET /buyers with buyer_type filter
   - GET /buyers with verification_status filter
   - GET /buyers/{buyer_id} individual lookup
4. Cleanup & pristine database baseline restoration (buyers=0, market_prices=100 intact).
5. CSV importer dry-run validation against buyers_template.csv.
"""

import sys
import os
import json
import uuid
import urllib.request
import urllib.error
from decimal import Decimal
from datetime import datetime, timezone
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

BASE_URL = "http://127.0.0.1:8000"

TEST_BUYER_1_ID = uuid.UUID("a1111111-1111-4111-8111-111111111111")
TEST_BUYER_2_ID = uuid.UUID("a2222222-2222-4222-8222-222222222222")


def make_request(method: str, path: str, data: dict = None) -> tuple:
    url = f"{BASE_URL}{path}"
    req_data = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
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


async def get_db_counts():
    async def _op(s):
        b = (await s.execute(select(func.count(Buyer.id)))).scalar() or 0
        mp = (await s.execute(select(func.count(MarketPrice.id)))).scalar() or 0
        f = (await s.execute(select(func.count(Field.id)))).scalar() or 0
        sat = (await s.execute(select(func.count(SatelliteObservation.id)))).scalar() or 0
        return b, mp, f, sat
    return await run_in_isolated_session(_op)


async def seed_isolated_test_buyers():
    async def _op(s):
        b1 = Buyer(
            id=TEST_BUYER_1_ID,
            business_name="TEST_Sri_Venkateswara_Rice_Mill",
            buyer_type="mill",
            district="Nellore",
            state="Andhra Pradesh",
            address_summary="Industrial Estate, Nellore",
            contact_person="Manager Test",
            contact_phone="+919876543210",
            contact_email="test.mill@example.com",
            preferred_varieties=["BPT 5204", "MTU 1010"],
            min_procurement_quintals=Decimal("50.00"),
            verification_status="verified",
            verification_notes="Empanelled CMR test unit",
            is_active=True,
        )
        b2 = Buyer(
            id=TEST_BUYER_2_ID,
            business_name="TEST_Rayalaseema_Paddy_FPO",
            buyer_type="fpo",
            district="Tirupati",
            state="Andhra Pradesh",
            address_summary="Market Yard, Tirupati",
            contact_person="President Test",
            contact_phone="+919123456789",
            contact_email="test.fpo@example.com",
            preferred_varieties=["Common"],
            min_procurement_quintals=Decimal("20.00"),
            verification_status="pending",
            verification_notes="Cooperative test unit",
            is_active=True,
        )
        s.add_all([b1, b2])
        await s.commit()
    await run_in_isolated_session(_op)


async def cleanup_test_buyers():
    async def _op(s):
        await s.execute(text("DELETE FROM buyers WHERE business_name LIKE 'TEST_%'"))
        await s.commit()
    await run_in_isolated_session(_op)


def run_tests():
    print("=" * 80)
    print("STEP 11H.1 — BUYER INFORMATION SOURCE AUDIT & ENDPOINT VERIFICATION")
    print("=" * 80)

    results = {}

    # 1. Baseline Database Inspection
    print("\n[CHECK 1] Verifying Current Database Baseline Counts...")
    b_cnt, mp_cnt, f_cnt, sat_cnt = asyncio.run(get_db_counts())
    print(f"  buyers:                 {b_cnt} (must be 0)")
    print(f"  market_prices:          {mp_cnt} (must be 100 genuine records)")
    print(f"  fields:                 {f_cnt} (must be 58)")
    print(f"  satellite_observations: {sat_cnt} (must be 580)")

    assert b_cnt == 0, f"Expected 0 buyers, found {b_cnt}"
    assert mp_cnt == 100, f"Expected 100 genuine market_prices, found {mp_cnt}"
    assert f_cnt == 58, f"Fields altered: {f_cnt}"
    assert sat_cnt == 580, f"Satellite observations altered: {sat_cnt}"
    print("  [PASS] Database baseline verified: buyers=0, market_prices=100, core data intact.")
    results["baseline_counts"] = "PASS"

    # 2. Empty-Database Endpoint Behavior
    print("\n[CHECK 2] Testing Buyer Endpoints on Empty Database...")

    # 2.1 GET /buyers
    st, res = make_request("GET", "/buyers")
    assert st == 200, f"Expected 200, got {st}: {res}"
    assert res["items"] == []
    assert res["total"] == 0
    assert res["skip"] == 0
    assert res["limit"] == 50
    print("  GET /buyers -> 200 OK (items=[], total=0)")

    # 2.2 GET /buyers?district=Chittoor
    st, res = make_request("GET", "/buyers?district=Chittoor")
    assert st == 200 and res["items"] == [] and res["total"] == 0
    print("  GET /buyers?district=Chittoor -> 200 OK (items=[], total=0)")

    # 2.3 GET /buyers?buyer_type=mill
    st, res = make_request("GET", "/buyers?buyer_type=mill")
    assert st == 200 and res["items"] == [] and res["total"] == 0
    print("  GET /buyers?buyer_type=mill -> 200 OK (items=[], total=0)")

    # 2.4 GET /buyers/{unknown_uuid}
    st, res = make_request("GET", f"/buyers/{uuid.uuid4()}")
    assert st == 404
    print(f"  GET /buyers/{{unknown_uuid}} -> 404 Not Found: {res.get('detail')}")

    # 2.5 GET /buyers/invalid-uuid
    st, res = make_request("GET", "/buyers/not-a-valid-uuid")
    assert st == 422
    print("  GET /buyers/not-a-valid-uuid -> 422 Unprocessable Entity (ValidationError)")

    print("  [PASS] Empty-database buyer endpoints behave strictly to specification.")
    results["empty_db_endpoints"] = "PASS"

    # 3. Seeded Isolation & Location/Type Filtering Tests
    print("\n[CHECK 3] Testing Seeded Buyer Filtering & Details in Isolation...")
    asyncio.run(seed_isolated_test_buyers())

    try:
        # Check total seeded
        st, res = make_request("GET", "/buyers")
        assert st == 200 and res["total"] == 2 and len(res["items"]) == 2
        print(f"  GET /buyers (seeded) -> 200 OK (total=2)")

        # Filter by district=Nellore
        st, res = make_request("GET", "/buyers?district=Nellore")
        assert st == 200 and res["total"] == 1
        assert res["items"][0]["business_name"] == "TEST_Sri_Venkateswara_Rice_Mill"
        assert res["items"][0]["buyer_type"] == "mill"
        print("  GET /buyers?district=Nellore -> 200 OK (filtered to 1 mill in Nellore)")

        # Filter by buyer_type=fpo
        st, res = make_request("GET", "/buyers?buyer_type=fpo")
        assert st == 200 and res["total"] == 1
        assert res["items"][0]["business_name"] == "TEST_Rayalaseema_Paddy_FPO"
        print("  GET /buyers?buyer_type=fpo -> 200 OK (filtered to 1 FPO in Tirupati)")

        # Filter by verification_status=verified
        st, res = make_request("GET", "/buyers?verification_status=verified")
        assert st == 200 and res["total"] == 1
        assert res["items"][0]["id"] == str(TEST_BUYER_1_ID)
        print("  GET /buyers?verification_status=verified -> 200 OK (verified only)")

        # Get by ID
        st, res = make_request("GET", f"/buyers/{TEST_BUYER_1_ID}")
        assert st == 200
        assert res["business_name"] == "TEST_Sri_Venkateswara_Rice_Mill"
        assert res["preferred_varieties"] == ["BPT 5204", "MTU 1010"]
        assert res["min_procurement_quintals"] == 50.0
        print(f"  GET /buyers/{TEST_BUYER_1_ID} -> 200 OK (details verified)")

    finally:
        # Clean ONLY test buyers
        print("\n[Teardown] Cleaning up isolated test buyers...")
        asyncio.run(cleanup_test_buyers())

    # 4. Verify Final Database Baseline
    print("\n[CHECK 4] Verifying Final Database Baseline Restoration...")
    b_cnt, mp_cnt, f_cnt, sat_cnt = asyncio.run(get_db_counts())
    print(f"  buyers:                 {b_cnt} (restored to 0)")
    print(f"  market_prices:          {mp_cnt} (preserved 100 genuine records)")
    print(f"  fields:                 {f_cnt} (intact 58)")
    print(f"  satellite_observations: {sat_cnt} (intact 580)")

    assert b_cnt == 0, f"Buyers table not cleaned: {b_cnt}"
    assert mp_cnt == 100, f"Market prices altered: {mp_cnt}"
    assert f_cnt == 58, f"Fields altered: {f_cnt}"
    assert sat_cnt == 580, f"Satellite observations altered: {sat_cnt}"
    print("  [PASS] Database restored cleanly to 0 buyers; genuine market data preserved.")
    results["teardown_restoration"] = "PASS"

    # 5. CSV Importer Dry-Run Validation
    print("\n[CHECK 5] Testing CSV Importer Dry-Run Against Template...")
    template_path = BACKEND_DIR / "data_templates" / "buyers_template.csv"
    assert template_path.exists(), "buyers_template.csv missing!"

    from scripts.import_market_buyer_csv import import_buyers
    count = asyncio.run(import_buyers(template_path, dry_run=True))
    print(f"  buyers_template.csv dry-run: {count} valid records parsed without error.")
    print("  [PASS] CSV importer validation rules confirmed operational.")
    results["csv_template_validation"] = "PASS"

    print("\n" + "=" * 80)
    print(f"ALL STEP 11H.1 AUDIT CHECKS PASSED ({len(results)}/{len(results)}) (100% PASS)")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_tests()
