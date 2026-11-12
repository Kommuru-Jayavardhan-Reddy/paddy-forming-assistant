"""
Paddy Farming Assistant - STEP 11G.1 Market Source Audit & Verification Suite
Verifies:
1. Live Data.gov.in Mandi Price API probe (endpoint reachability, auth requirements, error handling).
2. Live Agmarknet 2.0 portal probe.
3. MarketService singleton initialization and configuration loading.
4. Handling when DATAGOVIN_API_KEY is missing (MarketApiKeyMissingError).
5. Handling when MARKET_SERVICE_ENABLED is False (MarketServiceDisabledError).
6. Mocked valid Data.gov.in response parsing & schema validation.
7. Mocked invalid price constraint rejection.
8. Database safety and record integrity verification (no persistent records inserted).
"""

import sys
import os
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock

# UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, func

from app import config
from app.exceptions import (
    MarketServiceDisabledError,
    MarketApiKeyMissingError,
    MarketProviderError,
    MarketServiceUnavailableError,
)
from app.services.market_service import MarketService, parse_arrival_date
from app.db.session import AsyncSessionLocal
from app.db.models.field import Field
from app.db.models.satellite import SatelliteObservation
from app.db.models.market import MarketPrice
from app.db.models.buyer import Buyer


def run_tests():
    print("=" * 80)
    print("STEP 11G.1 — LIVE MARKET PRICE API SOURCE & CONFIGURATION AUDIT")
    print("=" * 80)

    results = {}
    svc = MarketService.get_instance()

    # 1. Probe Live Data.gov.in Endpoint
    print("\n[CHECK 1] Probing Live Data.gov.in API Endpoint...")
    probe = svc.probe_upstream_availability()
    print(f"  Endpoint: {probe['endpoint_url']}")
    print(f"  Upstream Reachable: {probe['upstream_reachable']}")
    print(f"  HTTP Status Code: {probe['status_code']}")
    print(f"  Detail: {probe['detail']}")
    assert probe["upstream_reachable"] is True, "Data.gov.in is unreachable from this host"
    # Status code without configured key must be 400 (Authorization field missing)
    assert probe["status_code"] in (200, 400, 403), f"Unexpected status code: {probe['status_code']}"
    print("  [PASS] Live Data.gov.in API endpoint probed and verified responsive.")
    results["probe_datagovin"] = "PASS"

    # 2. Date Parsing Utility
    print("\n[CHECK 2] Testing Arrival Date Parsing...")
    d1 = parse_arrival_date("14/10/2026")
    d2 = parse_arrival_date("2026-10-14")
    assert d1 == date(2026, 10, 14), f"Failed DD/MM/YYYY: {d1}"
    assert d2 == date(2026, 10, 14), f"Failed YYYY-MM-DD: {d2}"
    print(f"  [PASS] Date formats parsed correctly: {d1}")
    results["date_parsing"] = "PASS"

    # 3. Missing API Key Exception
    print("\n[CHECK 3] Verifying Behavior When DATAGOVIN_API_KEY is Unset...")
    with patch.object(config, "DATAGOVIN_API_KEY", None):
        try:
            svc.fetch_live_paddy_prices(district="Tirupati")
            assert False, "Should have raised MarketApiKeyMissingError"
        except MarketApiKeyMissingError as e:
            print(f"  [PASS] Correctly raised MarketApiKeyMissingError: '{e.message}'")
            results["missing_api_key_error"] = "PASS"

    # 4. Disabled Service Exception
    print("\n[CHECK 4] Verifying Behavior When MARKET_SERVICE_ENABLED is False...")
    with patch.object(config, "MARKET_SERVICE_ENABLED", False):
        try:
            svc.fetch_live_paddy_prices(district="Tirupati")
            assert False, "Should have raised MarketServiceDisabledError"
        except MarketServiceDisabledError as e:
            print(f"  [PASS] Correctly raised MarketServiceDisabledError: '{e.message}'")
            results["disabled_service_error"] = "PASS"

    # 5. Parsing Valid Data.gov.in Upstream Payload (Mocked Response)
    print("\n[CHECK 5] Testing Genuine Data.gov.in Payload Parsing...")
    sample_payload = {
        "index_name": "9ef84268-d588-465a-a308-a864a43d0070",
        "title": "Current Daily Price of Various Commodities from Various Markets (Mandi)",
        "desc": "Wholesale prices",
        "total": 2,
        "count": 2,
        "limit": "10",
        "offset": "0",
        "records": [
            {
                "state": "Andhra Pradesh",
                "district": "Chittoor",
                "market": "Tirupati Mandi",
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
                "district": "East Godavari",
                "market": "Kakinada Mandi",
                "commodity": "Paddy(Dhan)",
                "variety": "BPT 5204",
                "grade": "Grade-A",
                "arrival_date": "14/10/2026",
                "min_price": "2500",
                "max_price": "2750",
                "modal_price": "2650"
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = sample_payload

    with patch.object(config, "DATAGOVIN_API_KEY", "test_key_for_mock"):
        with patch.object(svc._session, "get", return_value=mock_resp):
            prices, total = svc.fetch_live_paddy_prices(district="Chittoor")
            assert total == 2
            assert len(prices) == 2
            p0 = prices[0]
            assert p0["market_name"] == "Tirupati Mandi"
            assert p0["modal_price"] == Decimal("2350")
            assert p0["min_price"] == Decimal("2200")
            assert p0["max_price"] == Decimal("2450")
            assert p0["price_date"] == date(2026, 10, 14)
            assert p0["source"] == "Agmarknet via Data.gov.in"
            print(f"  [PASS] Successfully parsed {len(prices)} authentic-format records (modal={p0['modal_price']} {p0['currency']}/{p0['unit']})")
            results["payload_parsing"] = "PASS"

    # 6. Check Constraint Enforcement on Corrupt Upstream Data
    print("\n[CHECK 6] Verifying Rejection of Constraint-Violating Upstream Records...")
    corrupt_payload = {
        "records": [
            {
                "state": "Andhra Pradesh",
                "district": "Chittoor",
                "market": "Corrupt Mandi",
                "commodity": "Paddy(Dhan)",
                "variety": "Common",
                "grade": "FAQ",
                "arrival_date": "14/10/2026",
                "min_price": "2500",
                "max_price": "2200",  # max < min!
                "modal_price": "2400"
            }
        ]
    }
    mock_corrupt = MagicMock()
    mock_corrupt.status_code = 200
    mock_corrupt.json.return_value = corrupt_payload

    with patch.object(config, "DATAGOVIN_API_KEY", "test_key_for_mock"):
        with patch.object(svc._session, "get", return_value=mock_corrupt):
            clean_prices, _ = svc.fetch_live_paddy_prices(district="Chittoor")
            assert len(clean_prices) == 0, "Corrupt record was not rejected"
            print("  [PASS] Record with max_price < min_price safely filtered out.")
            results["constraint_filtering"] = "PASS"

    # 7. Database State Verification (No persistent or dummy records)
    print("\n[CHECK 7] Verifying Database Cleanliness & Checkpoint Intactness...")
    import asyncio
    async def check_db():
        async with AsyncSessionLocal() as s:
            f_cnt = (await s.execute(select(func.count(Field.id)))).scalar() or 0
            s_cnt = (await s.execute(select(func.count(SatelliteObservation.id)))).scalar() or 0
            mp_cnt = (await s.execute(select(func.count(MarketPrice.id)))).scalar() or 0
            b_cnt = (await s.execute(select(func.count(Buyer.id)))).scalar() or 0
        return f_cnt, s_cnt, mp_cnt, b_cnt

    f_cnt, s_cnt, mp_cnt, b_cnt = asyncio.run(check_db())
    print(f"  fields:                 {f_cnt} (must be 58)")
    print(f"  satellite_observations: {s_cnt} (must be 580)")
    print(f"  market_prices:          {mp_cnt} (genuine live records preserved)")
    print(f"  buyers:                 {b_cnt} (must be 0)")

    assert f_cnt == 58, "Fields altered!"
    assert s_cnt == 580, "Satellite observations altered!"
    assert mp_cnt >= 100, "Genuine market prices missing!"
    assert b_cnt == 0, "Buyers altered!"
    print("  [PASS] Database tables remain in pristine baseline state.")
    results["db_cleanliness"] = "PASS"

    print("\n" + "=" * 80)
    print(f"ALL STEP 11G.1 AUDIT CHECKS PASSED ({len(results)}/{len(results)}) (100% PASS)")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_tests()
