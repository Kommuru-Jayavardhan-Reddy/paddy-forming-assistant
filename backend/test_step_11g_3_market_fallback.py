"""
Paddy Farming Assistant - STEP 11G.3 Live vs Local Fallback Strategy Test Suite
Verifies:
1. Baseline database state (58 fields, 580 satellite, 0 market, 0 buyers).
2. Missing local data + missing API key -> 200 OK empty response (data_source='empty', is_stale=False).
3. Missing local data + valid API credentials -> fetches upstream, caches to DB, returns (data_source='live_synced').
4. Fresh local data (< 3 days) -> serves from DB cache without contacting upstream (data_source='database_cache').
5. Stale local data (> 3 days) + missing API key -> serves local with clear stale flag (data_source='database_stale', is_stale=True).
6. Stale local data + valid API key + upstream timeout/failure -> graceful degradation to local stale cache (is_stale=True).
7. Upstream empty results -> 200 OK with empty items list (data_source='empty').
8. Database cache-write failure handling -> graceful transaction rollback without crash.
9. Cooldown rate limiting & force_live override.
10. Existing endpoint schema compatibility (GET /market/prices, GET /market/prices/latest).
11. Complete teardown & pristine database row count restoration.
"""

import sys
import os
import time
import asyncio
import threading
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

# UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests
import requests.exceptions
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
from app.db.models.field import Field
from app.db.models.satellite import SatelliteObservation
from app.db.models.market import MarketPrice
from app.db.models.buyer import Buyer
from app.services.market_service import MarketService, parse_arrival_date

PORT = 8015
BASE_URL = f"http://127.0.0.1:{PORT}"


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


async def get_db_counts():
    async with AsyncSessionLocal() as s:
        f_cnt = (await s.execute(select(func.count(Field.id)))).scalar() or 0
        s_cnt = (await s.execute(select(func.count(SatelliteObservation.id)))).scalar() or 0
        mp_cnt = (await s.execute(select(func.count(MarketPrice.id)))).scalar() or 0
        b_cnt = (await s.execute(select(func.count(Buyer.id)))).scalar() or 0
    return f_cnt, s_cnt, mp_cnt, b_cnt


async def cleanup_test_market_data():
    async with AsyncSessionLocal() as s:
        await s.execute(text("DELETE FROM market_prices WHERE source LIKE '%Data.gov.in%' OR market_name LIKE 'TEST%'"))
        await s.commit()


async def seed_stale_record(stale_date: date):
    async with AsyncSessionLocal() as s:
        p = MarketPrice(
            market_name="TEST_Stale_Nellore",
            district="SPSR Nellore",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="BPT 5204",
            grade="FAQ",
            min_price=Decimal("2400"),
            max_price=Decimal("2600"),
            modal_price=Decimal("2500"),
            price_date=stale_date,
            source="Agmarknet via Data.gov.in",
        )
        s.add(p)
        await s.commit()


def run_tests():
    print("=" * 80)
    print("STEP 11G.3 — LIVE VS LOCAL MARKET PRICE FALLBACK STRATEGY")
    print("=" * 80)

    # 1. Pre-test Database Verification
    f_cnt, s_cnt, mp_cnt, b_cnt = asyncio.run(get_db_counts())
    reset_db_singletons()

    print(f"Pre-test Database Row Counts:")
    print(f"  fields:                 {f_cnt} (must be 58)")
    print(f"  satellite_observations: {s_cnt} (must be 580)")
    print(f"  market_prices:          {mp_cnt} (must be 0)")
    print(f"  buyers:                 {b_cnt} (must be 0)")
    assert f_cnt == 58, "Fields altered!"
    assert s_cnt == 580, "Satellite observations altered!"
    assert mp_cnt == 0, "Market prices baseline contaminated!"
    assert b_cnt == 0, "Buyers baseline contaminated!"

    results = {}
    svc = MarketService.get_instance()
    svc.clear_cooldowns()

    today_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    live_payload = {
        "total": 2,
        "count": 2,
        "records": [
            {
                "state": "Andhra Pradesh",
                "district": "Chittoor",
                "market": "TEST_Tirupati_Yard",
                "commodity": "Paddy(Dhan)",
                "variety": "Common",
                "grade": "FAQ",
                "arrival_date": today_str,
                "min_price": "2250",
                "max_price": "2450",
                "modal_price": "2350"
            },
            {
                "state": "Andhra Pradesh",
                "district": "Chittoor",
                "market": "TEST_Madanapalle_Yard",
                "commodity": "Paddy(Dhan)",
                "variety": "Grade-A",
                "grade": "FAQ",
                "arrival_date": today_str,
                "min_price": "2400",
                "max_price": "2600",
                "modal_price": "2500"
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = live_payload

    # =========================================================================
    # PHASE 1: Empty Table, Live Sync, and Fresh Cache Hits (Server 1)
    # =========================================================================
    print("\n[Setup 1] Starting server for Phase 1 tests...")
    server1 = ServerThread(port=PORT)
    server1.start()
    assert wait_for_server(BASE_URL), "Phase 1 test server failed to start!"
    print("  [OK] Server 1 online at", BASE_URL)

    try:
        # CHECK 1: Missing local data + Missing API key
        print("\n[CHECK 1] Querying with empty DB and no API key configured...")
        with patch.object(config, "DATAGOVIN_API_KEY", None):
            resp = requests.get(f"{BASE_URL}/market/prices?district=Chittoor")
            print(f"  Status: {resp.status_code}")
            data = resp.json()
            print(f"  Response: total={data['total']}, data_source={data.get('data_source')}, is_stale={data.get('is_stale')}")
            assert resp.status_code == 200
            assert data["total"] == 0
            assert len(data["items"]) == 0
            assert data["data_source"] == "empty"
            assert data["is_stale"] is False
            print("  [PASS] Clean empty response returned without fabricating data.")
            results["missing_data_no_key"] = "PASS"

        # CHECK 2: Missing local data + Valid API key -> Live sync & cache
        print("\n[CHECK 2] Querying with empty DB and valid API key (triggers live sync)...")
        with patch.object(config, "DATAGOVIN_API_KEY", "test_valid_key"):
            with patch.object(svc._session, "get", return_value=mock_resp) as mock_get:
                resp = requests.get(f"{BASE_URL}/market/prices?district=Chittoor")
                assert resp.status_code == 200
                data = resp.json()
                print(f"  Live Synced: total={data['total']}, data_source={data['data_source']}, is_stale={data['is_stale']}")
                assert data["total"] == 2
                assert len(data["items"]) == 2
                assert data["data_source"] == "live_synced"
                assert data["is_stale"] is False
                assert mock_get.called, "Upstream GET should have been called"
                print("  [PASS] Live data fetched, cached in PostgreSQL, and returned with live_synced metadata.")
                results["missing_data_with_key"] = "PASS"

        # CHECK 3: Fresh local data -> Cache hit (No upstream call)
        print("\n[CHECK 3] Querying when fresh local records exist (Cache Hit)...")
        with patch.object(config, "DATAGOVIN_API_KEY", "test_valid_key"):
            with patch.object(svc._session, "get") as mock_get_fail:
                mock_get_fail.side_effect = AssertionError("Upstream should NOT be contacted for fresh local data!")
                resp = requests.get(f"{BASE_URL}/market/prices?district=Chittoor")
                assert resp.status_code == 200
                data = resp.json()
                print(f"  Cache Hit: total={data['total']}, data_source={data['data_source']}, is_stale={data['is_stale']}")
                assert data["total"] == 2
                assert data["data_source"] == "database_cache"
                assert data["is_stale"] is False
                assert not mock_get_fail.called
                print("  [PASS] Fresh local records served instantly from database cache without network call.")
                results["fresh_local_cache_hit"] = "PASS"

        # CHECK 4: Upstream returns empty results for unknown district
        print("\n[CHECK 4] Upstream returns empty results for unknown district...")
        svc.clear_cooldowns()
        mock_empty = MagicMock()
        mock_empty.status_code = 200
        mock_empty.json.return_value = {"records": [], "total": 0}

        with patch.object(config, "DATAGOVIN_API_KEY", "test_valid_key"):
            with patch.object(svc._session, "get", return_value=mock_empty):
                resp = requests.get(f"{BASE_URL}/market/prices?district=UnknownDistrict")
                assert resp.status_code == 200
                data = resp.json()
                print(f"  Empty Result: total={data['total']}, data_source={data['data_source']}")
                assert data["total"] == 0
                assert len(data["items"]) == 0
                assert data["data_source"] == "empty"
                print("  [PASS] Empty upstream response safely handled with data_source='empty'.")
                results["empty_upstream_handling"] = "PASS"

        # CHECK 5: Database cache-write failure handling during live sync
        print("\n[CHECK 5] Database cache write failure handling during live sync...")
        svc.clear_cooldowns()
        with patch.object(config, "DATAGOVIN_API_KEY", "test_valid_key"):
            with patch.object(svc._session, "get", return_value=mock_resp):
                from app.db.repositories.other_repositories import MarketPriceRepository
                with patch.object(MarketPriceRepository, "upsert_prices", side_effect=OperationalError("db error", {}, Exception())):
                    resp = requests.get(f"{BASE_URL}/market/prices?district=Chittoor&force_live=true")
                    print(f"  DB Write Failure Status: {resp.status_code}")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert "items" in data
                    print("  [PASS] Database cache-write failure handled gracefully without 500 crash.")
                    results["db_write_failure_degradation"] = "PASS"

        # CHECK 6: Cooldown rate limiting & force_live override
        print("\n[CHECK 6] Testing sync cooldown rate limiting and force_live override...")
        svc.clear_cooldowns()
        assert not svc.is_in_cooldown("Andhra Pradesh", "Chittoor")
        svc.record_sync_attempt("Andhra Pradesh", "Chittoor")
        assert svc.is_in_cooldown("Andhra Pradesh", "Chittoor")

        # Stale record with cooldown active -> should NOT call upstream
        with patch.object(config, "DATAGOVIN_API_KEY", "test_valid_key"):
            with patch.object(svc._session, "get") as mock_should_not_call:
                mock_should_not_call.side_effect = AssertionError("Cooldown violated!")
                resp = requests.get(f"{BASE_URL}/market/prices?district=Chittoor")
                assert resp.status_code == 200
                assert not mock_should_not_call.called

        # When force_live=True -> should bypass cooldown and call upstream
        with patch.object(config, "DATAGOVIN_API_KEY", "test_valid_key"):
            with patch.object(svc._session, "get", return_value=mock_resp) as mock_force:
                resp = requests.get(f"{BASE_URL}/market/prices?district=Chittoor&force_live=true")
                assert resp.status_code == 200
                assert mock_force.called
        print("  [PASS] Cooldown prevents redundant upstream calls; force_live bypasses cooldown.")
        results["cooldown_and_force_live"] = "PASS"

        # CHECK 7: GET /market/prices/latest Compatibility
        print("\n[CHECK 7] Testing GET /market/prices/latest fallback integration...")
        resp = requests.get(f"{BASE_URL}/market/prices/latest")
        assert resp.status_code == 200
        data = resp.json()
        print(f"  Latest Prices: total={data['total']}, data_source={data['data_source']}")
        assert "items" in data
        assert "total" in data
        assert "data_source" in data
        print("  [PASS] GET /market/prices/latest integrates seamlessly with fallback strategy.")
        results["latest_prices_compatibility"] = "PASS"

    finally:
        server1.stop()
        time.sleep(0.5)
        reset_db_singletons()
        print("  [OK] Server 1 stopped.")

    # =========================================================================
    # PHASE 2: Stale Data Fallback & Degradation Tests (Server 2)
    # =========================================================================
    print("\n[Setup 2] Seeding stale market record on main thread...")
    stale_date = datetime.now(timezone.utc).date() - timedelta(days=10)
    asyncio.run(seed_stale_record(stale_date))
    reset_db_singletons()
    print("  [OK] Stale record seeded for SPSR Nellore (price_date = %s)." % stale_date)

    print("\n[Setup 3] Starting server for Phase 2 tests...")
    server2 = ServerThread(port=PORT)
    server2.start()
    assert wait_for_server(BASE_URL), "Phase 2 test server failed to start!"
    print("  [OK] Server 2 online at", BASE_URL)

    try:
        # CHECK 8: Stale local data + Missing API key
        print("\n[CHECK 8] Querying stale records when API key is missing...")
        with patch.object(config, "DATAGOVIN_API_KEY", None):
            resp = requests.get(f"{BASE_URL}/market/prices?district=SPSR+Nellore")
            assert resp.status_code == 200
            data = resp.json()
            print(f"  Stale Fallback: total={data['total']}, data_source={data['data_source']}, is_stale={data['is_stale']}, freshness={data.get('freshness_date')}")
            assert data["total"] == 1
            assert data["data_source"] == "database_stale"
            assert data["is_stale"] is True
            assert data["freshness_date"] == stale_date.isoformat()
            print("  [PASS] Stale records returned with clear is_stale=True indicator; never presented as current live.")
            results["stale_local_no_key"] = "PASS"

        # CHECK 9: Stale local data + Upstream Timeout -> Graceful degradation
        print("\n[CHECK 9] Upstream network timeout fallback to stale records...")
        svc.clear_cooldowns()
        with patch.object(config, "DATAGOVIN_API_KEY", "test_valid_key"):
            with patch.object(svc._session, "get", side_effect=requests.exceptions.Timeout("Read timeout")):
                resp = requests.get(f"{BASE_URL}/market/prices?district=SPSR+Nellore")
                assert resp.status_code == 200
                data = resp.json()
                print(f"  Timeout Fallback: total={data['total']}, data_source={data['data_source']}, is_stale={data['is_stale']}")
                assert data["total"] == 1
                assert data["data_source"] == "database_stale"
                assert data["is_stale"] is True
                print("  [PASS] Upstream timeout intercepted gracefully; served stale local record with no HTTP 500 error.")
                results["upstream_timeout_fallback"] = "PASS"

        # CHECK 10: Upstream 403 Forbidden / Provider Error Fallback
        print("\n[CHECK 10] Upstream HTTP 403 error fallback to stale records...")
        svc.clear_cooldowns()
        mock_403 = MagicMock()
        mock_403.status_code = 403
        mock_403.text = '{"error": "Key not authorised"}'
        mock_403.json.return_value = {"error": "Key not authorised"}

        with patch.object(config, "DATAGOVIN_API_KEY", "test_valid_key"):
            with patch.object(svc._session, "get", return_value=mock_403):
                resp = requests.get(f"{BASE_URL}/market/prices?district=SPSR+Nellore")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 1
                assert data["data_source"] == "database_stale"
                assert data["is_stale"] is True
                print("  [PASS] Upstream 403 intercepted gracefully; served stale records safely.")
                results["upstream_error_fallback"] = "PASS"

    finally:
        server2.stop()
        time.sleep(0.5)
        reset_db_singletons()
        print("  [OK] Server 2 stopped.")

    # =========================================================================
    # TEARDOWN & BASELINE RESTORATION
    # =========================================================================
    print("\n[Teardown] Cleaning test data from database on main thread...")
    asyncio.run(cleanup_test_market_data())
    reset_db_singletons()
    print("  [OK] Test data cleaned.")

    f_cnt, s_cnt, mp_cnt, b_cnt = asyncio.run(get_db_counts())
    reset_db_singletons()

    print(f"\nPost-cleanup Database Row Counts:")
    print(f"  fields:                 {f_cnt} (must be 58)")
    print(f"  satellite_observations: {s_cnt} (must be 580)")
    print(f"  market_prices:          {mp_cnt} (must be 0)")
    print(f"  buyers:                 {b_cnt} (must be 0)")
    assert f_cnt == 58, "Fields altered during test!"
    assert s_cnt == 580, "Satellite observations altered during test!"
    assert mp_cnt == 0, "Market prices not fully cleaned up!"
    assert b_cnt == 0, "Buyers altered during test!"
    print("  [PASS] Pristine database baseline verified.")
    results["baseline_restoration"] = "PASS"

    print("\n" + "=" * 80)
    print(f"ALL STEP 11G.3 TESTS PASSED ({len(results)}/{len(results)}) (100% PASS)")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_tests()
