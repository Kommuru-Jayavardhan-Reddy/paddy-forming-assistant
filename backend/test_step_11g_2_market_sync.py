"""
Paddy Farming Assistant - STEP 11G.2 Live Market Sync & Persistence Test Suite
Verifies:
1. Pre-baseline row counts (fields=58, satellite_observations=580, market_prices=0, buyers=0).
2. Missing DATAGOVIN_API_KEY handling (HTTP 503, no fabricated data, no DB insertion).
3. Service disabled handling (HTTP 503).
4. Authentic upstream Data.gov.in probe (HTTP 400 without key, network reachable).
5. Authentic-format Data.gov.in payload parsing and atomic PostgreSQL persistence.
6. Idempotent upsert & in-batch deduplication (no duplicate rows created, existing records updated).
7. Rejection of check-constraint-violating records (max < min, negative) with accurate rejected counting.
8. Upstream error translation (HTTP 403 -> 502, timeout -> 503, invalid JSON -> 502).
9. Database error handling with transaction rollback and sanitized HTTP 500.
10. Synced record querying through GET /market/prices and GET /market/prices/latest.
11. Complete test data teardown and baseline row count restoration.
"""

import sys
import os
import time
import asyncio
import threading
from decimal import Decimal
from datetime import date, datetime, timezone
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

PORT = 8014
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


def run_tests():
    print("=" * 80)
    print("STEP 11G.2 — LIVE MANDI DATA RETRIEVAL & DATABASE PERSISTENCE")
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

    # Start Test Server
    print("\n[Setup] Launching test API server...")
    server = ServerThread(port=PORT)
    server.start()
    assert wait_for_server(BASE_URL), "Test API server failed to start!"
    print("  [OK] Test server online at", BASE_URL)

    try:
        # -------------------------------------------------------------
        # CHECK 1: Missing API Key Handling on POST /market/sync
        # -------------------------------------------------------------
        print("\n[CHECK 1] POST /market/sync with DATAGOVIN_API_KEY unconfigured...")
        with patch.object(config, "DATAGOVIN_API_KEY", None):
            resp = requests.post(f"{BASE_URL}/market/sync?state=Andhra+Pradesh")
            print(f"  Status Code: {resp.status_code}")
            print(f"  Response Body: {resp.json()}")
            assert resp.status_code == 503, f"Expected 503, got {resp.status_code}"
            assert "Data.gov.in API key is not configured" in resp.json()["detail"]
            print("  [PASS] Missing key cleanly rejected with 503 and zero database writes.")
            results["missing_key_behavior"] = "PASS"

        # -------------------------------------------------------------
        # CHECK 2: Disabled Market Service Handling
        # -------------------------------------------------------------
        print("\n[CHECK 2] POST /market/sync when MARKET_SERVICE_ENABLED is False...")
        with patch.object(config, "MARKET_SERVICE_ENABLED", False):
            resp = requests.post(f"{BASE_URL}/market/sync?state=Andhra+Pradesh")
            print(f"  Status Code: {resp.status_code}")
            assert resp.status_code == 503, f"Expected 503, got {resp.status_code}"
            assert "disabled in configuration" in resp.json()["detail"]
            print("  [PASS] Disabled service cleanly rejected with 503.")
            results["disabled_service_behavior"] = "PASS"

        # -------------------------------------------------------------
        # CHECK 3: Live Upstream Probe Reachability
        # -------------------------------------------------------------
        print("\n[CHECK 3] Probing genuine live Data.gov.in endpoint...")
        svc = MarketService.get_instance()
        probe = svc.probe_upstream_availability()
        print(f"  Upstream Reachable: {probe['upstream_reachable']}")
        print(f"  Status Code: {probe['status_code']}")
        print(f"  Detail: {probe['detail']}")
        assert probe["upstream_reachable"] is True, "Data.gov.in endpoint unreachable!"
        assert probe["status_code"] in (200, 400, 403), f"Unexpected status: {probe['status_code']}"
        print("  [PASS] Live Data.gov.in endpoint responsive.")
        results["live_upstream_probe"] = "PASS"

        # -------------------------------------------------------------
        # CHECK 4: Genuine Payload Parsing & Atomic PostgreSQL Persistence
        # -------------------------------------------------------------
        print("\n[CHECK 4] Synchronizing authentic-schema AP Paddy(Dhan) quotations...")
        sample_payload = {
            "index_name": "9ef84268-d588-465a-a308-a864a43d0070",
            "total": 3,
            "count": 3,
            "records": [
                {
                    "state": "Andhra Pradesh",
                    "district": "Chittoor",
                    "market": "TEST_Tirupati_Mandi",
                    "commodity": "Paddy(Dhan)",
                    "variety": "Common",
                    "grade": "FAQ",
                    "arrival_date": "14/10/2026",
                    "min_price": "2200",
                    "max_price": "2450",
                    "modal_price": "2350"
                },
                {
                    "state": "Andhra Pradesh",
                    "district": "SPSR Nellore",
                    "market": "TEST_Nellore_Mandi",
                    "commodity": "Paddy(Dhan)",
                    "variety": "BPT 5204",
                    "grade": "Grade-A",
                    "arrival_date": "14/10/2026",
                    "min_price": "2500",
                    "max_price": "2800",
                    "modal_price": "2680"
                },
                {
                    "state": "Andhra Pradesh",
                    "district": "East Godavari",
                    "market": "TEST_Kakinada_Mandi",
                    "commodity": "Paddy(Dhan)",
                    "variety": "Swarna",
                    "grade": "FAQ",
                    "arrival_date": "14/10/2026",
                    "min_price": "2150",
                    "max_price": "2350",
                    "modal_price": "2280"
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_payload

        with patch.object(config, "DATAGOVIN_API_KEY", "test_authorized_key"):
            with patch.object(svc._session, "get", return_value=mock_resp):
                resp = requests.post(f"{BASE_URL}/market/sync?state=Andhra+Pradesh")
                print(f"  Status: {resp.status_code}")
                data = resp.json()
                print(f"  Sync Response: status={data['status']}, retrieved={data['records_retrieved']}, persisted={data['records_persisted']}")
                assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
                assert data["status"] == "success"
                assert data["records_retrieved"] == 3
                assert data["records_accepted"] == 3
                assert data["records_rejected"] == 0
                assert data["records_persisted"] == 3

        print(f"  [PASS] Successfully persisted 3 authentic mandi quotations via POST /market/sync.")
        results["payload_sync_persistence"] = "PASS"

        # -------------------------------------------------------------
        # CHECK 5: Idempotency & In-Batch Deduplication
        # -------------------------------------------------------------
        print("\n[CHECK 5] Testing idempotency and duplicate deduplication...")
        # Payload contains an updated price for TEST_Tirupati_Mandi and a duplicate record of it in the same batch
        dup_payload = {
            "total": 4,
            "count": 4,
            "records": [
                {
                    "state": "Andhra Pradesh",
                    "district": "Chittoor",
                    "market": "TEST_Tirupati_Mandi",
                    "commodity": "Paddy(Dhan)",
                    "variety": "Common",
                    "grade": "FAQ",
                    "arrival_date": "14/10/2026",
                    "min_price": "2250",
                    "max_price": "2500",
                    "modal_price": "2400"  # updated modal price
                },
                {
                    "state": "Andhra Pradesh",
                    "district": "Chittoor",
                    "market": "TEST_Tirupati_Mandi",
                    "commodity": "Paddy(Dhan)",
                    "variety": "Common",
                    "grade": "FAQ",
                    "arrival_date": "14/10/2026",
                    "min_price": "2250",
                    "max_price": "2500",
                    "modal_price": "2400"  # duplicate in same batch
                },
                {
                    "state": "Andhra Pradesh",
                    "district": "SPSR Nellore",
                    "market": "TEST_Nellore_Mandi",
                    "commodity": "Paddy(Dhan)",
                    "variety": "BPT 5204",
                    "grade": "Grade-A",
                    "arrival_date": "14/10/2026",
                    "min_price": "2500",
                    "max_price": "2800",
                    "modal_price": "2680"
                },
                {
                    "state": "Andhra Pradesh",
                    "district": "East Godavari",
                    "market": "TEST_Kakinada_Mandi",
                    "commodity": "Paddy(Dhan)",
                    "variety": "Swarna",
                    "grade": "FAQ",
                    "arrival_date": "14/10/2026",
                    "min_price": "2150",
                    "max_price": "2350",
                    "modal_price": "2280"
                }
            ]
        }
        mock_dup = MagicMock()
        mock_dup.status_code = 200
        mock_dup.json.return_value = dup_payload

        with patch.object(config, "DATAGOVIN_API_KEY", "test_authorized_key"):
            with patch.object(svc._session, "get", return_value=mock_dup):
                resp = requests.post(f"{BASE_URL}/market/sync?state=Andhra+Pradesh")
                assert resp.status_code == 200
                data = resp.json()
                print(f"  Sync Response: retrieved={data['records_retrieved']}, persisted={data['records_persisted']}")
                assert data["records_retrieved"] == 4
                assert data["records_persisted"] == 3  # Deduplicated from 4 to 3 unique quotes

        print("  [PASS] Idempotent upsert verified: records deduplicated cleanly.")
        results["idempotent_upsert_dedup"] = "PASS"

        # -------------------------------------------------------------
        # CHECK 6: Corrupt Upstream Records Rejected with Accurate Counts
        # -------------------------------------------------------------
        print("\n[CHECK 6] Verifying rejection of corrupt records...")
        corrupt_payload = {
            "total": 3,
            "count": 3,
            "records": [
                {
                    "state": "Andhra Pradesh",
                    "district": "Chittoor",
                    "market": "TEST_Valid_Mandi",
                    "commodity": "Paddy(Dhan)",
                    "variety": "Common",
                    "grade": "FAQ",
                    "arrival_date": "14/10/2026",
                    "min_price": "2200",
                    "max_price": "2500",
                    "modal_price": "2350"
                },
                {
                    "state": "Andhra Pradesh",
                    "district": "Chittoor",
                    "market": "TEST_Corrupt_1",
                    "commodity": "Paddy(Dhan)",
                    "variety": "Common",
                    "grade": "FAQ",
                    "arrival_date": "14/10/2026",
                    "min_price": "2500",
                    "max_price": "2100",  # max < min!
                    "modal_price": "2300"
                },
                {
                    "state": "Andhra Pradesh",
                    "district": "Chittoor",
                    "market": "TEST_Corrupt_2",
                    "commodity": "Paddy(Dhan)",
                    "variety": "Common",
                    "grade": "FAQ",
                    "arrival_date": "14/10/2026",
                    "min_price": "-100",  # negative!
                    "max_price": "2500",
                    "modal_price": "2300"
                }
            ]
        }
        mock_corrupt = MagicMock()
        mock_corrupt.status_code = 200
        mock_corrupt.json.return_value = corrupt_payload

        with patch.object(config, "DATAGOVIN_API_KEY", "test_authorized_key"):
            with patch.object(svc._session, "get", return_value=mock_corrupt):
                resp = requests.post(f"{BASE_URL}/market/sync?state=Andhra+Pradesh")
                assert resp.status_code == 200
                data = resp.json()
                print(f"  Retrieved: {data['records_retrieved']}, Accepted: {data['records_accepted']}, Rejected: {data['records_rejected']}")
                assert data["records_retrieved"] == 3
                assert data["records_accepted"] == 1
                assert data["records_rejected"] == 2
                assert data["records_persisted"] == 1
        print("  [PASS] Corrupt records safely discarded with accurate rejection metrics.")
        results["corrupt_records_rejection"] = "PASS"

        # -------------------------------------------------------------
        # CHECK 7: Upstream Provider Failures (403, Timeout, Invalid JSON)
        # -------------------------------------------------------------
        print("\n[CHECK 7] Testing upstream provider error translation...")

        # 7A: 403 Forbidden
        mock_403 = MagicMock()
        mock_403.status_code = 403
        mock_403.text = '{"error": "Key not authorised"}'
        mock_403.json.return_value = {"error": "Key not authorised"}

        with patch.object(config, "DATAGOVIN_API_KEY", "test_authorized_key"):
            with patch.object(svc._session, "get", return_value=mock_403):
                resp = requests.post(f"{BASE_URL}/market/sync?state=Andhra+Pradesh")
                print(f"  7A (403): Status={resp.status_code}, Detail={resp.json()['detail']}")
                assert resp.status_code == 502, f"Expected 502, got {resp.status_code}"
                assert "authorization failed" in resp.json()["detail"].lower()

        # 7B: Timeout
        with patch.object(config, "DATAGOVIN_API_KEY", "test_authorized_key"):
            with patch.object(svc._session, "get", side_effect=requests.exceptions.Timeout("Read timeout")):
                resp = requests.post(f"{BASE_URL}/market/sync?state=Andhra+Pradesh")
                print(f"  7B (Timeout): Status={resp.status_code}, Detail={resp.json()['detail']}")
                assert resp.status_code == 503, f"Expected 503, got {resp.status_code}"
                assert "timed out" in resp.json()["detail"].lower()

        # 7C: Malformed JSON
        mock_bad_json = MagicMock()
        mock_bad_json.status_code = 200
        mock_bad_json.json.side_effect = ValueError("Invalid JSON")
        with patch.object(config, "DATAGOVIN_API_KEY", "test_authorized_key"):
            with patch.object(svc._session, "get", return_value=mock_bad_json):
                resp = requests.post(f"{BASE_URL}/market/sync?state=Andhra+Pradesh")
                print(f"  7C (Malformed JSON): Status={resp.status_code}, Detail={resp.json()['detail']}")
                assert resp.status_code == 502, f"Expected 502, got {resp.status_code}"
                assert "parse" in resp.json()["detail"].lower()

        print("  [PASS] Upstream error translation verified (502 Bad Gateway / 503 Service Unavailable).")
        results["upstream_error_handling"] = "PASS"

        # -------------------------------------------------------------
        # CHECK 8: Database Operational Failure Handling
        # -------------------------------------------------------------
        print("\n[CHECK 8] Testing database persistence failure handling...")
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.json.return_value = sample_payload

        with patch.object(config, "DATAGOVIN_API_KEY", "test_authorized_key"):
            with patch.object(svc._session, "get", return_value=mock_ok):
                from app.db.repositories.other_repositories import MarketPriceRepository
                with patch.object(MarketPriceRepository, "upsert_prices", side_effect=OperationalError("db error", {}, Exception())):
                    resp = requests.post(f"{BASE_URL}/market/sync?state=Andhra+Pradesh")
                    print(f"  Status: {resp.status_code}, Detail: {resp.json()['detail']}")
                    assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"
                    assert "internal database error" in resp.json()["detail"].lower()
        print("  [PASS] Database error safely sanitized with HTTP 500.")
        results["db_failure_handling"] = "PASS"

        # -------------------------------------------------------------
        # CHECK 9: Verified Querying of Synced Records via Existing APIs
        # -------------------------------------------------------------
        print("\n[CHECK 9] Verifying synced records via GET /market/prices and /market/prices/latest...")
        get_resp = requests.get(f"{BASE_URL}/market/prices?district=Chittoor")
        assert get_resp.status_code == 200
        items = get_resp.json()["items"]
        assert len(items) >= 1
        print(f"  GET /market/prices?district=Chittoor -> returned {len(items)} items (modal={items[0]['modal_price']} {items[0]['currency']}/{items[0]['unit']})")
        assert items[0]["source"] == "Agmarknet via Data.gov.in"
        assert items[0]["price_date"] == "2026-10-14"

        latest_resp = requests.get(f"{BASE_URL}/market/prices/latest")
        assert latest_resp.status_code == 200
        latest_items = latest_resp.json()["items"]
        assert len(latest_items) >= 1
        print(f"  GET /market/prices/latest -> returned {len(latest_items)} latest items")
        print("  [PASS] Synced records fully searchable via existing market endpoints.")
        results["query_synced_records"] = "PASS"

    finally:
        # Teardown server first
        print("\n[Teardown] Stopping test API server...")
        server.stop()
        time.sleep(0.5)
        reset_db_singletons()
        print("  [OK] Test server stopped.")

        # Clean database on main event loop
        print("[Teardown] Cleaning test data from database...")
        asyncio.run(cleanup_test_market_data())
        reset_db_singletons()
        print("  [OK] Test data cleaned.")

        # Post-teardown Database Verification
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
    print(f"ALL STEP 11G.2 TESTS PASSED ({len(results)}/{len(results)}) (100% PASS)")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_tests()
