"""
Paddy Farming Assistant - STEP 11F.10.1 Market Prices & Buyers API Test Suite
Exhaustively tests:
1. Empty table responses:
   - GET /market/prices -> 200 OK, items=[], total=0
   - GET /market/prices/latest -> 200 OK, items=[], total=0
   - GET /buyers -> 200 OK, items=[], total=0
   - GET /buyers/{unknown_uuid} -> 404 Not Found
   - GET /buyers/invalid-uuid -> 422 Unprocessable Entity
2. Controlled test data seeding (isolated, strictly tracked).
3. Seeded table HTTP API operations:
   - GET /market/prices (serialization, types, fields)
   - GET /market/prices with district filter
   - GET /market/prices with variety filter
   - GET /market/prices with non-existent filter
   - GET /market/prices pagination (skip, limit)
   - GET /market/prices/latest (deterministic price_date DESC ordering)
   - GET /buyers (serialization, preferred_varieties list)
   - GET /buyers with buyer_type filter
   - GET /buyers with district filter
   - GET /buyers/{buyer_id} for existing buyer
   - GET /buyers/{unknown_uuid} -> 404 Not Found
   - GET /buyers/invalid-uuid -> 422 Unprocessable Entity
   - DB error handling sanitization
   - Existing endpoints regression (/health, /fields/FIELD_01, /timeseries)
4. Complete cleanup of test records and post-test row count verification.
"""

import sys
import os
import time
import uuid
import asyncio
import threading
from decimal import Decimal
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests
import uvicorn
from sqlalchemy import text, select, func
from sqlalchemy.exc import OperationalError

from app import config
from app.main import app
from app.db.session import (
    AsyncSessionLocal,
    check_db_connectivity,
    close_db_engine,
)
from app.db.models.market import MarketPrice
from app.db.models.buyer import Buyer
from app.db.models.field import Field
from app.db.models.satellite import SatelliteObservation
from app.db.repositories.other_repositories import MarketPriceRepository, BuyerRepository

PORT = 8012
BASE_URL = f"http://127.0.0.1:{PORT}"

TEST_BUYER_1_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
TEST_BUYER_2_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")


class ServerThread(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = PORT):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        cfg = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="error",
            access_log=False,
        )
        self.server = uvicorn.Server(cfg)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


def wait_for_server(base_url: str, timeout: float = 20.0) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get(f"{base_url}/health", timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def reset_db_singletons():
    import app.db.session as sm
    sm._async_engine = None
    sm._async_session_factory = None


async def verify_pre_baseline():
    async with AsyncSessionLocal() as s:
        f_cnt = (await s.execute(select(func.count(Field.id)))).scalar() or 0
        s_cnt = (await s.execute(select(func.count(SatelliteObservation.id)))).scalar() or 0
        mp_cnt = (await s.execute(select(func.count(MarketPrice.id)))).scalar() or 0
        b_cnt = (await s.execute(select(func.count(Buyer.id)))).scalar() or 0

    print(f"Pre-test Database Row Counts:")
    print(f"  fields:                 {f_cnt} (must be 58)")
    print(f"  satellite_observations: {s_cnt} (must be 580)")
    print(f"  market_prices:          {mp_cnt} (baseline)")
    print(f"  buyers:                 {b_cnt} (baseline)")

    assert f_cnt == 58, f"Unexpected fields count: {f_cnt}"
    assert s_cnt == 580, f"Unexpected satellite count: {s_cnt}"
    assert mp_cnt == 0, f"market_prices not empty: {mp_cnt}"
    assert b_cnt == 0, f"buyers not empty: {b_cnt}"


async def seed_test_data():
    async with AsyncSessionLocal() as s:
        mp1 = MarketPrice(
            market_name="TEST_APMC_Tirupati",
            district="Tirupati",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="Common",
            grade="FAQ",
            min_price=Decimal("2200.00"),
            max_price=Decimal("2400.00"),
            modal_price=Decimal("2300.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 10),
            source="Agmarknet Test",
        )
        mp2 = MarketPrice(
            market_name="TEST_APMC_Kakinada",
            district="East Godavari",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="BPT 5204",
            grade="Grade-A",
            min_price=Decimal("2500.00"),
            max_price=Decimal("2750.00"),
            modal_price=Decimal("2650.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 12),
            source="Agmarknet Test",
        )
        mp3 = MarketPrice(
            market_name="TEST_APMC_Nellore",
            district="Nellore",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="Common",
            grade="FAQ",
            min_price=Decimal("2300.00"),
            max_price=Decimal("2500.00"),
            modal_price=Decimal("2400.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 14),
            source="Agmarknet Test",
        )
        s.add_all([mp1, mp2, mp3])

        b1 = Buyer(
            id=TEST_BUYER_1_ID,
            business_name="TEST Sri Lakshmi Rice Mill",
            buyer_type="mill",
            district="East Godavari",
            state="Andhra Pradesh",
            address_summary="Industrial Area Kakinada",
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
            business_name="TEST Rayalaseema FPO",
            buyer_type="fpo",
            district="Tirupati",
            state="Andhra Pradesh",
            address_summary="Market Yard Tirupati",
            contact_person="President Test",
            contact_phone="+919123456789",
            contact_email="test.fpo@example.com",
            preferred_varieties=["Common"],
            min_procurement_quintals=Decimal("20.00"),
            verification_status="verified",
            verification_notes="Cooperative society test",
            is_active=True,
        )
        s.add_all([b1, b2])
        await s.commit()
    print("  [OK] Seeded 3 test market_prices and 2 test buyers.")


async def cleanup_test_data():
    async with AsyncSessionLocal() as s:
        await s.execute(text("DELETE FROM market_prices WHERE market_name LIKE 'TEST_%'"))
        await s.execute(text("DELETE FROM buyers WHERE business_name LIKE 'TEST %'"))
        await s.commit()

        final_f = (await s.execute(select(func.count(Field.id)))).scalar() or 0
        final_s = (await s.execute(select(func.count(SatelliteObservation.id)))).scalar() or 0
        final_mp = (await s.execute(select(func.count(MarketPrice.id)))).scalar() or 0
        final_b = (await s.execute(select(func.count(Buyer.id)))).scalar() or 0

    print(f"\nPost-cleanup Database Row Counts:")
    print(f"  fields:                 {final_f} (must be 58)")
    print(f"  satellite_observations: {final_s} (must be 580)")
    print(f"  market_prices:          {final_mp} (must be 0)")
    print(f"  buyers:                 {final_b} (must be 0)")

    assert final_f == 58, "Fields altered!"
    assert final_s == 580, "Satellite observations altered!"
    assert final_mp == 0, f"market_prices not cleaned: {final_mp}"
    assert final_b == 0, f"buyers not cleaned: {final_b}"


def run_empty_table_tests(results: dict):
    print("\n--- PHASE 1: Empty Table HTTP Responses ---")

    # 1. GET /market/prices
    r = requests.get(f"{BASE_URL}/market/prices")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["items"] == [] and data["total"] == 0
    print(f"  [PASS] GET /market/prices (empty) -> 200 OK, total={data['total']}, items=[]")
    results["empty_market_prices"] = "PASS"

    # 2. GET /market/prices/latest
    r = requests.get(f"{BASE_URL}/market/prices/latest")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["items"] == [] and data["total"] == 0
    print(f"  [PASS] GET /market/prices/latest (empty) -> 200 OK, total={data['total']}, items=[]")
    results["empty_market_prices_latest"] = "PASS"

    # 3. GET /buyers
    r = requests.get(f"{BASE_URL}/buyers")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["items"] == [] and data["total"] == 0
    print(f"  [PASS] GET /buyers (empty) -> 200 OK, total={data['total']}, items=[]")
    results["empty_buyers"] = "PASS"

    # 4. GET /buyers/{unknown_uuid} on empty table
    rnd_id = uuid.uuid4()
    r = requests.get(f"{BASE_URL}/buyers/{rnd_id}")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    assert f"Buyer '{rnd_id}' was not found" in r.json()["detail"]
    print(f"  [PASS] GET /buyers/{rnd_id} (empty table) -> 404 Not Found")
    results["empty_buyer_404"] = "PASS"

    # 5. GET /buyers/invalid-uuid -> 422
    r = requests.get(f"{BASE_URL}/buyers/not-a-valid-uuid")
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
    print(f"  [PASS] GET /buyers/not-a-valid-uuid -> 422 Unprocessable Entity")
    results["invalid_uuid_422"] = "PASS"


def run_seeded_table_tests(results: dict):
    print("\n--- PHASE 2: Seeded Table HTTP API Operations ---")

    # 6. GET /market/prices
    r = requests.get(f"{BASE_URL}/market/prices")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    item0 = data["items"][0]
    assert "id" in item0 and "market_name" in item0 and "modal_price" in item0
    assert isinstance(item0["min_price"], float)
    assert isinstance(item0["modal_price"], float)
    assert item0["currency"] == "INR"
    assert item0["unit"] == "Quintal"
    print(f"  [PASS] GET /market/prices -> 200 OK, total={data['total']}, schema verified ({item0['market_name']})")
    results["market_prices_list"] = "PASS"

    # 7. GET /market/prices with district filter
    r = requests.get(f"{BASE_URL}/market/prices?district=Tirupati")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["district"] == "Tirupati"
    assert data["items"][0]["modal_price"] == 2300.0
    print(f"  [PASS] GET /market/prices?district=Tirupati -> 200 OK, modal={data['items'][0]['modal_price']}")
    results["market_prices_district_filter"] = "PASS"

    # 8. GET /market/prices with variety filter
    r = requests.get(f"{BASE_URL}/market/prices?variety=BPT%205204")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["variety"] == "BPT 5204"
    assert data["items"][0]["modal_price"] == 2650.0
    print(f"  [PASS] GET /market/prices?variety=BPT 5204 -> 200 OK, modal={data['items'][0]['modal_price']}")
    results["market_prices_variety_filter"] = "PASS"

    # 9. GET /market/prices with non-existent filter
    r = requests.get(f"{BASE_URL}/market/prices?district=UnknownDistrict")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0 and data["items"] == []
    print(f"  [PASS] GET /market/prices?district=UnknownDistrict -> 200 OK, total=0, items=[]")
    results["market_prices_empty_filter"] = "PASS"

    # 10. GET /market/prices pagination
    r = requests.get(f"{BASE_URL}/market/prices?skip=1&limit=1")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1
    assert data["skip"] == 1 and data["limit"] == 1
    print(f"  [PASS] GET /market/prices?skip=1&limit=1 -> 200 OK, paginated item returned")
    results["market_prices_pagination"] = "PASS"

    # 11. GET /market/prices/latest (Ordering verification: price_date DESC)
    r = requests.get(f"{BASE_URL}/market/prices/latest?limit=2")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    d0 = data["items"][0]["price_date"]
    d1 = data["items"][1]["price_date"]
    assert d0 >= d1, f"Expected descending date order: {d0} >= {d1}"
    assert data["items"][0]["market_name"] == "TEST_APMC_Nellore"
    assert data["items"][1]["market_name"] == "TEST_APMC_Kakinada"
    print(f"  [PASS] GET /market/prices/latest -> 200 OK, strictly ordered: {d0} -> {d1}")
    results["market_prices_latest_ordering"] = "PASS"

    # 12. GET /buyers (All seeded)
    r = requests.get(f"{BASE_URL}/buyers")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    b0 = data["items"][0]
    assert "business_name" in b0 and "buyer_type" in b0 and "preferred_varieties" in b0
    assert isinstance(b0["preferred_varieties"], list)
    print(f"  [PASS] GET /buyers -> 200 OK, total={data['total']}, schema verified ({b0['business_name']})")
    results["buyers_list"] = "PASS"

    # 13. GET /buyers with buyer_type filter
    r = requests.get(f"{BASE_URL}/buyers?buyer_type=mill")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["buyer_type"] == "mill"
    assert data["items"][0]["business_name"] == "TEST Sri Lakshmi Rice Mill"
    print(f"  [PASS] GET /buyers?buyer_type=mill -> 200 OK, {data['items'][0]['business_name']}")
    results["buyers_type_filter"] = "PASS"

    # 14. GET /buyers with district filter
    r = requests.get(f"{BASE_URL}/buyers?district=Tirupati")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["district"] == "Tirupati"
    assert data["items"][0]["business_name"] == "TEST Rayalaseema FPO"
    print(f"  [PASS] GET /buyers?district=Tirupati -> 200 OK, {data['items'][0]['business_name']}")
    results["buyers_district_filter"] = "PASS"

    # 15. GET /buyers/{buyer_id} for existing buyer
    r = requests.get(f"{BASE_URL}/buyers/{TEST_BUYER_1_ID}")
    assert r.status_code == 200
    b_data = r.json()
    assert b_data["id"] == str(TEST_BUYER_1_ID)
    assert b_data["business_name"] == "TEST Sri Lakshmi Rice Mill"
    assert b_data["buyer_type"] == "mill"
    assert "BPT 5204" in b_data["preferred_varieties"]
    assert b_data["min_procurement_quintals"] == 50.0
    print(f"  [PASS] GET /buyers/{TEST_BUYER_1_ID} -> 200 OK, matched existing buyer profile")
    results["buyer_detail_success"] = "PASS"

    # 16. GET /buyers/{unknown_uuid} -> 404 Not Found
    unknown_id = uuid.uuid4()
    r = requests.get(f"{BASE_URL}/buyers/{unknown_id}")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    assert f"Buyer '{unknown_id}' was not found" in r.json()["detail"]
    print(f"  [PASS] GET /buyers/{unknown_id} -> 404 Not Found with clean message")
    results["buyer_detail_not_found_404"] = "PASS"

    # 17. Database Error Handling Sanitization
    with patch.object(MarketPriceRepository, "list_latest_prices", side_effect=OperationalError("connection failure", None, None)):
        r_fail = requests.get(f"{BASE_URL}/market/prices")
        assert r_fail.status_code == 500
        err_json = r_fail.json()
        assert "internal database error" in err_json["detail"]
        assert "connection failure" not in err_json["detail"]  # No SQL / driver leak
        print(f"  [PASS] DB failure gracefully handled -> HTTP 500 sanitized: '{err_json['detail']}'")
    results["db_error_sanitization"] = "PASS"

    # 18. Existing Endpoints Regression Check
    r_health = requests.get(f"{BASE_URL}/health")
    assert r_health.status_code == 200 and r_health.json()["status"] == "healthy"
    r_field = requests.get(f"{BASE_URL}/fields/FIELD_01")
    assert r_field.status_code == 200 and r_field.json()["field_id"] == "FIELD_01"
    r_ts = requests.get(f"{BASE_URL}/fields/FIELD_01/timeseries")
    assert r_ts.status_code == 200 and r_ts.json()["total_timesteps"] == 10
    print(f"  [PASS] Regression check: /health, /fields/FIELD_01, /timeseries operate normally")
    results["existing_endpoints_regression"] = "PASS"


def main():
    print("=" * 80)
    print("STEP 11F.10.1 — MARKET PRICES & BUYERS API INTEGRATION TEST SUITE")
    print("=" * 80)

    # 1. Baseline verification
    asyncio.run(verify_pre_baseline())
    reset_db_singletons()

    results = {}

    # 2. Start server for Empty Table Tests
    print("\n[Setup 1] Starting test server for empty-table verification...")
    server1 = ServerThread(port=PORT)
    server1.start()
    assert wait_for_server(BASE_URL), f"Test server failed to start on port {PORT}"
    print("  [OK] Test server online.")

    try:
        run_empty_table_tests(results)
    finally:
        server1.stop()
        time.sleep(0.5)
        reset_db_singletons()
        print("  [OK] Server 1 stopped.")

    # 3. Seed isolated test data
    print("\n[Setup 2] Seeding isolated test records...")
    asyncio.run(seed_test_data())
    reset_db_singletons()

    # 4. Start server for Seeded Table Tests
    print("\n[Setup 3] Starting test server for seeded-table verification...")
    server2 = ServerThread(port=PORT)
    server2.start()
    assert wait_for_server(BASE_URL), f"Test server failed to start on port {PORT}"
    print("  [OK] Test server online.")

    try:
        run_seeded_table_tests(results)
    finally:
        server2.stop()
        time.sleep(0.5)
        reset_db_singletons()
        print("  [OK] Server 2 stopped.")

    # 5. Cleanup test data and verify final baseline
    print("\n[Teardown] Cleaning up test data...")
    asyncio.run(cleanup_test_data())
    reset_db_singletons()

    print("\n" + "=" * 80)
    print(f"ALL STEP 11F.10.1 TESTS PASSED ({len(results)}/{len(results)}) (100% PASS)")
    print("=" * 80)
    return results


if __name__ == "__main__":
    main()
