"""
Paddy Farming Assistant - STEP 11G.4 Mandi Price Analytics and Trend Aggregations Test Suite

Exhaustively verifies:
1. Baseline database verification (58 fields, 580 satellite, 0 market_prices, 0 buyers).
2. Empty table analytics responses:
   - GET /market/analytics/summary -> 200 OK, has_data=False, total_observations=0, null stats
   - GET /market/analytics/trends?days=7 -> 200 OK, days_with_data=0, trend_direction='insufficient_data'
   - GET /market/analytics/districts -> 200 OK, state_avg_modal_price=None, districts=[]
   - GET /market/analytics/varieties -> 200 OK, premium_variety=None, standard_variety=None, varieties=[]
3. Single observation analytics:
   - GET /market/analytics/summary -> 200 OK, total_observations=1, min==max==modal
   - GET /market/analytics/trends -> 200 OK, days_with_data=1, trend_direction='insufficient_data', absolute_change=None
   - GET /market/analytics/districts -> 200 OK, 1 district, price_spread=0.0
   - GET /market/analytics/varieties -> 200 OK, 1 variety, premium==standard
4. Multi-date, multi-district, multi-variety dataset analytics:
   - GET /market/analytics/summary (aggregations: avg, min, max modal prices, distinct counts)
   - GET /market/analytics/trends?days=7 & days=30 (ordered daily time series, net change, direction)
   - GET /market/analytics/districts (state average, district differentials, highest/lowest, price spread)
   - GET /market/analytics/varieties (variety averages, premium variety, standard variety)
   - Filtered analytics by district and variety
5. Missing historical periods / unmatched filters -> valid empty response, no data fabrication
6. Invalid parameters (days=0, days=-5, days=91) -> 422 Unprocessable Entity
7. Database error handling -> 500 Internal Server Error with sanitized error detail
8. Regression on existing market endpoints (/market/prices, /market/prices/latest, /health)
9. Complete teardown & pristine baseline restoration (market_prices = 0).
"""

import sys
import os
import time
import asyncio
import threading
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
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
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app import config
from app.main import app
from app.db.session import (
    get_database_url,
    check_db_connectivity,
    close_db_engine,
)
from app.db.models.market import MarketPrice
from app.db.models.buyer import Buyer
from app.db.models.field import Field
from app.db.models.satellite import SatelliteObservation
from app.db.repositories.other_repositories import MarketPriceRepository

PORT = 8016
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


async def run_in_isolated_session(coro_fn):
    """
    Executes an async database operation in an isolated engine using NullPool.
    Ensures zero cross-thread event loop connection leaks with asyncpg.
    """
    engine = create_async_engine(get_database_url(), poolclass=NullPool)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        result = await coro_fn(session)
    await engine.dispose()
    return result


async def get_db_counts():
    async def _op(s):
        f_cnt = (await s.execute(select(func.count(Field.id)))).scalar() or 0
        s_cnt = (await s.execute(select(func.count(SatelliteObservation.id)))).scalar() or 0
        mp_cnt = (await s.execute(select(func.count(MarketPrice.id)))).scalar() or 0
        b_cnt = (await s.execute(select(func.count(Buyer.id)))).scalar() or 0
        return f_cnt, s_cnt, mp_cnt, b_cnt
    return await run_in_isolated_session(_op)


async def cleanup_test_market_data():
    async def _op(s):
        await s.execute(text("DELETE FROM market_prices WHERE market_name LIKE 'TEST_%'"))
        await s.commit()
    await run_in_isolated_session(_op)


async def seed_single_observation():
    async def _op(s):
        p = MarketPrice(
            market_name="TEST_Mandi_Tirupati_Single",
            district="Chittoor",
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
            source="Agmarknet Analytics Test",
        )
        s.add(p)
        await s.commit()
    await run_in_isolated_session(_op)


async def seed_multi_observations():
    """
    Seeds 9 authentic-format records across 4 dates, 3 districts, and 3 varieties.
    Dates: 2026-10-08, 2026-10-10, 2026-10-12, 2026-10-14.
    Districts: Chittoor, Nellore, East Godavari.
    Varieties: Common, Grade-A, BPT 5204.
    """
    records = [
        # 2026-10-08 (Earliest date: avg modal = (2200 + 2300) / 2 = 2250.0)
        MarketPrice(
            market_name="TEST_Mandi_Tirupati_1",
            district="Chittoor",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="Common",
            grade="FAQ",
            min_price=Decimal("2150.00"),
            max_price=Decimal("2250.00"),
            modal_price=Decimal("2200.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 8),
            source="Agmarknet Analytics Test",
        ),
        MarketPrice(
            market_name="TEST_Mandi_Nellore_1",
            district="Nellore",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="Common",
            grade="FAQ",
            min_price=Decimal("2250.00"),
            max_price=Decimal("2350.00"),
            modal_price=Decimal("2300.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 8),
            source="Agmarknet Analytics Test",
        ),
        # 2026-10-10 (Day 2: avg modal = (2400 + 2700) / 2 = 2550.0)
        MarketPrice(
            market_name="TEST_Mandi_Madanapalle_2",
            district="Chittoor",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="Grade-A",
            grade="Grade-A",
            min_price=Decimal("2350.00"),
            max_price=Decimal("2450.00"),
            modal_price=Decimal("2400.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 10),
            source="Agmarknet Analytics Test",
        ),
        MarketPrice(
            market_name="TEST_Mandi_Kakinada_2",
            district="East Godavari",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="BPT 5204",
            grade="FAQ",
            min_price=Decimal("2600.00"),
            max_price=Decimal("2800.00"),
            modal_price=Decimal("2700.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 10),
            source="Agmarknet Analytics Test",
        ),
        # 2026-10-12 (Day 3: avg modal = (2350 + 2500) / 2 = 2425.0)
        MarketPrice(
            market_name="TEST_Mandi_Nellore_3",
            district="Nellore",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="Common",
            grade="FAQ",
            min_price=Decimal("2300.00"),
            max_price=Decimal("2400.00"),
            modal_price=Decimal("2350.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 12),
            source="Agmarknet Analytics Test",
        ),
        MarketPrice(
            market_name="TEST_Mandi_Rajahmundry_3",
            district="East Godavari",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="Grade-A",
            grade="Grade-A",
            min_price=Decimal("2450.00"),
            max_price=Decimal("2550.00"),
            modal_price=Decimal("2500.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 12),
            source="Agmarknet Analytics Test",
        ),
        # 2026-10-14 (Latest date: avg modal = (2450 + 2800 + 2400) / 3 = 2550.0)
        MarketPrice(
            market_name="TEST_Mandi_Tirupati_4",
            district="Chittoor",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="Common",
            grade="FAQ",
            min_price=Decimal("2400.00"),
            max_price=Decimal("2500.00"),
            modal_price=Decimal("2450.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 14),
            source="Agmarknet Analytics Test",
        ),
        MarketPrice(
            market_name="TEST_Mandi_Nellore_4",
            district="Nellore",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="BPT 5204",
            grade="FAQ",
            min_price=Decimal("2750.00"),
            max_price=Decimal("2850.00"),
            modal_price=Decimal("2800.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 14),
            source="Agmarknet Analytics Test",
        ),
        MarketPrice(
            market_name="TEST_Mandi_Kakinada_4",
            district="East Godavari",
            state="Andhra Pradesh",
            commodity="Paddy (Dhan)",
            variety="Common",
            grade="FAQ",
            min_price=Decimal("2350.00"),
            max_price=Decimal("2450.00"),
            modal_price=Decimal("2400.00"),
            currency="INR",
            unit="Quintal",
            price_date=date(2026, 10, 14),
            source="Agmarknet Analytics Test",
        ),
    ]

    async def _op(s):
        s.add_all(records)
        await s.commit()
    await run_in_isolated_session(_op)


def run_empty_db_tests(results: dict):
    print("\n--- PHASE 1: Empty Database Analytics Operations ---")

    # 1. GET /market/analytics/summary
    r = requests.get(f"{BASE_URL}/market/analytics/summary")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["has_data"] is False
    assert data["total_observations"] == 0
    assert data["avg_modal_price"] is None
    assert data["min_modal_price"] is None
    assert data["max_modal_price"] is None
    assert data["earliest_price_date"] is None
    assert data["latest_price_date"] is None
    assert data["currency"] == "INR"
    assert data["unit"] == "Quintal"
    print(f"  [PASS] GET /market/analytics/summary (empty) -> 200 OK, has_data=False, total=0, avg=None")
    results["empty_summary"] = "PASS"

    # 2. GET /market/analytics/trends?days=7
    r = requests.get(f"{BASE_URL}/market/analytics/trends?days=7")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["days_requested"] == 7
    assert data["days_with_data"] == 0
    assert data["total_observations"] == 0
    assert data["trend_direction"] == "insufficient_data"
    assert data["start_modal_price"] is None
    assert data["end_modal_price"] is None
    assert data["absolute_change"] is None
    assert data["percentage_change"] is None
    assert data["daily_trends"] == []
    print(f"  [PASS] GET /market/analytics/trends?days=7 (empty) -> 200 OK, trend_direction='insufficient_data', daily_trends=[]")
    results["empty_trends_7"] = "PASS"

    # 3. GET /market/analytics/trends?days=30
    r = requests.get(f"{BASE_URL}/market/analytics/trends?days=30")
    assert r.status_code == 200
    data = r.json()
    assert data["days_requested"] == 30
    assert data["trend_direction"] == "insufficient_data"
    print(f"  [PASS] GET /market/analytics/trends?days=30 (empty) -> 200 OK, trend_direction='insufficient_data'")
    results["empty_trends_30"] = "PASS"

    # 4. GET /market/analytics/districts
    r = requests.get(f"{BASE_URL}/market/analytics/districts")
    assert r.status_code == 200
    data = r.json()
    assert data["state_avg_modal_price"] is None
    assert data["highest_price_district"] is None
    assert data["lowest_price_district"] is None
    assert data["price_spread"] is None
    assert data["districts"] == []
    print(f"  [PASS] GET /market/analytics/districts (empty) -> 200 OK, state_avg=None, districts=[]")
    results["empty_districts"] = "PASS"

    # 5. GET /market/analytics/varieties
    r = requests.get(f"{BASE_URL}/market/analytics/varieties")
    assert r.status_code == 200
    data = r.json()
    assert data["premium_variety"] is None
    assert data["standard_variety"] is None
    assert data["varieties"] == []
    print(f"  [PASS] GET /market/analytics/varieties (empty) -> 200 OK, premium=None, standard=None, varieties=[]")
    results["empty_varieties"] = "PASS"


def run_single_observation_tests(results: dict):
    print("\n--- PHASE 2: Single Persisted Observation Analytics ---")

    # 6. GET /market/analytics/summary (single record)
    r = requests.get(f"{BASE_URL}/market/analytics/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["has_data"] is True
    assert data["total_observations"] == 1
    assert data["distinct_markets"] == 1
    assert data["distinct_districts"] == 1
    assert data["distinct_varieties"] == 1
    assert data["avg_modal_price"] == 2300.0
    assert data["min_modal_price"] == 2300.0
    assert data["max_modal_price"] == 2300.0
    assert data["min_transaction_price"] == 2200.0
    assert data["max_transaction_price"] == 2400.0
    assert data["earliest_price_date"] == "2026-10-10"
    assert data["latest_price_date"] == "2026-10-10"
    print(f"  [PASS] GET /market/analytics/summary (single obs) -> 200 OK, avg_modal={data['avg_modal_price']}, total=1")
    results["single_obs_summary"] = "PASS"

    # 7. GET /market/analytics/trends (single record -> insufficient_data)
    r = requests.get(f"{BASE_URL}/market/analytics/trends?days=7")
    assert r.status_code == 200
    data = r.json()
    assert data["days_with_data"] == 1
    assert data["total_observations"] == 1
    assert data["trend_direction"] == "insufficient_data"
    assert data["absolute_change"] is None
    assert data["percentage_change"] is None
    assert data["start_modal_price"] == 2300.0
    assert data["end_modal_price"] == 2300.0
    assert len(data["daily_trends"]) == 1
    assert data["daily_trends"][0]["date"] == "2026-10-10"
    assert data["daily_trends"][0]["avg_modal_price"] == 2300.0
    print(f"  [PASS] GET /market/analytics/trends (single obs) -> 200 OK, strictly insufficient_data (no false trend)")
    results["single_obs_trends_insufficient"] = "PASS"

    # 8. GET /market/analytics/districts (single record)
    r = requests.get(f"{BASE_URL}/market/analytics/districts")
    assert r.status_code == 200
    data = r.json()
    assert data["state_avg_modal_price"] == 2300.0
    assert data["highest_price_district"] == "Chittoor"
    assert data["lowest_price_district"] == "Chittoor"
    assert data["price_spread"] == 0.0
    assert len(data["districts"]) == 1
    d0 = data["districts"][0]
    assert d0["district"] == "Chittoor"
    assert d0["avg_modal_price"] == 2300.0
    assert d0["difference_from_state_avg"] == 0.0
    print(f"  [PASS] GET /market/analytics/districts (single obs) -> 200 OK, 1 district, spread=0.0")
    results["single_obs_districts"] = "PASS"

    # 9. GET /market/analytics/varieties (single record)
    r = requests.get(f"{BASE_URL}/market/analytics/varieties")
    assert r.status_code == 200
    data = r.json()
    assert data["premium_variety"] == "Common"
    assert data["standard_variety"] == "Common"
    assert len(data["varieties"]) == 1
    v0 = data["varieties"][0]
    assert v0["variety"] == "Common"
    assert v0["avg_modal_price"] == 2300.0
    print(f"  [PASS] GET /market/analytics/varieties (single obs) -> 200 OK, variety='Common', avg=2300.0")
    results["single_obs_varieties"] = "PASS"


def run_multi_observation_tests(results: dict):
    print("\n--- PHASE 3: Multi-Date, Multi-District, Multi-Variety Dataset Analytics ---")

    # 10. GET /market/analytics/summary (overall dataset: 9 records)
    r = requests.get(f"{BASE_URL}/market/analytics/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["has_data"] is True
    assert data["total_observations"] == 9
    assert data["distinct_markets"] >= 6
    assert data["distinct_districts"] == 3
    assert data["distinct_varieties"] == 3
    # Sum of modal prices: 2200+2300+2400+2700+2350+2500+2450+2800+2400 = 22100. Avg = 22100 / 9 = 2455.56
    assert abs(data["avg_modal_price"] - 2455.56) < 0.1, f"Expected ~2455.56, got {data['avg_modal_price']}"
    assert data["min_modal_price"] == 2200.0
    assert data["max_modal_price"] == 2800.0
    assert data["min_transaction_price"] == 2150.0
    assert data["max_transaction_price"] == 2850.0
    assert data["earliest_price_date"] == "2026-10-08"
    assert data["latest_price_date"] == "2026-10-14"
    print(f"  [PASS] GET /market/analytics/summary (9 obs) -> 200 OK, avg_modal={data['avg_modal_price']}, min={data['min_modal_price']}, max={data['max_modal_price']}")
    results["multi_obs_summary"] = "PASS"

    # 11. GET /market/analytics/trends?days=7 (4 dates within 7 days)
    r = requests.get(f"{BASE_URL}/market/analytics/trends?days=7")
    assert r.status_code == 200
    data = r.json()
    assert data["days_requested"] == 7
    assert data["days_with_data"] == 4
    assert data["total_observations"] == 9
    assert data["start_date"] == "2026-10-08"
    assert data["end_date"] == "2026-10-14"
    # start_modal_price on 2026-10-08 = (2200+2300)/2 = 2250.0
    # end_modal_price on 2026-10-14 = (2450+2800+2400)/3 = 2550.0
    # absolute_change = 2550.0 - 2250.0 = +300.0
    # percentage_change = (300 / 2250) * 100 = +13.33%
    # trend_direction = "up"
    assert data["start_modal_price"] == 2250.0
    assert data["end_modal_price"] == 2550.0
    assert data["absolute_change"] == 300.0
    assert abs(data["percentage_change"] - 13.33) < 0.1
    assert data["trend_direction"] == "up"
    assert len(data["daily_trends"]) == 4
    # Check ascending chronological sort
    dates = [p["date"] for p in data["daily_trends"]]
    assert dates == sorted(dates), f"Dates not strictly ascending: {dates}"
    print(f"  [PASS] GET /market/analytics/trends?days=7 -> 200 OK, change=+{data['absolute_change']} INR (+{data['percentage_change']}%), trend='{data['trend_direction']}'")
    results["multi_obs_trends_up"] = "PASS"

    # 12. GET /market/analytics/trends?days=30
    r = requests.get(f"{BASE_URL}/market/analytics/trends?days=30")
    assert r.status_code == 200
    data = r.json()
    assert data["days_requested"] == 30
    assert data["days_with_data"] == 4
    assert data["trend_direction"] == "up"
    print(f"  [PASS] GET /market/analytics/trends?days=30 -> 200 OK, days_with_data=4, trend='up'")
    results["multi_obs_trends_30"] = "PASS"

    # 13. GET /market/analytics/districts (district ranking & differentials)
    r = requests.get(f"{BASE_URL}/market/analytics/districts")
    assert r.status_code == 200
    data = r.json()
    assert data["days_analyzed"] == 30
    assert abs(data["state_avg_modal_price"] - 2455.56) < 0.1
    assert len(data["districts"]) == 3
    # Check descending order of avg_modal_price
    dist_avgs = [d["avg_modal_price"] for d in data["districts"]]
    assert dist_avgs == sorted(dist_avgs, reverse=True), f"Districts not sorted descending: {dist_avgs}"
    assert data["highest_price_district"] == data["districts"][0]["district"]
    assert data["lowest_price_district"] == data["districts"][-1]["district"]
    assert data["price_spread"] == round(data["districts"][0]["avg_modal_price"] - data["districts"][-1]["avg_modal_price"], 2)
    for d in data["districts"]:
        assert d["currency"] == "INR"
        assert d["unit"] == "Quintal"
        assert "difference_from_state_avg" in d
        assert "percentage_diff_from_state_avg" in d
        assert "market_count" in d
    print(f"  [PASS] GET /market/analytics/districts -> 200 OK, highest='{data['highest_price_district']}', lowest='{data['lowest_price_district']}', spread={data['price_spread']} INR")
    results["multi_obs_districts"] = "PASS"

    # 14. GET /market/analytics/varieties (variety ranking, premium & standard)
    r = requests.get(f"{BASE_URL}/market/analytics/varieties")
    assert r.status_code == 200
    data = r.json()
    assert len(data["varieties"]) == 3
    # BPT 5204 (2700, 2800 -> avg 2750.0)
    # Grade-A (2400, 2500 -> avg 2450.0)
    # Common (2200, 2300, 2350, 2450, 2400 -> avg 2340.0)
    assert data["premium_variety"] == "BPT 5204"
    assert data["standard_variety"] == "Common"
    var_avgs = [v["avg_modal_price"] for v in data["varieties"]]
    assert var_avgs == sorted(var_avgs, reverse=True), f"Varieties not sorted descending: {var_avgs}"
    print(f"  [PASS] GET /market/analytics/varieties -> 200 OK, premium='{data['premium_variety']}', standard='{data['standard_variety']}'")
    results["multi_obs_varieties"] = "PASS"

    # 15. Filtered Analytics: District filter (Chittoor only)
    r = requests.get(f"{BASE_URL}/market/analytics/summary?district=Chittoor")
    assert r.status_code == 200
    data = r.json()
    assert data["total_observations"] == 3
    assert data["district"] == "Chittoor"
    assert data["distinct_districts"] == 1
    # Chittoor modal prices: 2200, 2400, 2450 -> avg = 7050 / 3 = 2350.0
    assert data["avg_modal_price"] == 2350.0
    print(f"  [PASS] GET /market/analytics/summary?district=Chittoor -> 200 OK, total=3, avg=2350.0")
    results["filtered_district_summary"] = "PASS"

    # 16. Filtered Analytics: Variety filter (BPT 5204 only)
    r = requests.get(f"{BASE_URL}/market/analytics/summary?variety=BPT%205204")
    assert r.status_code == 200
    data = r.json()
    assert data["total_observations"] == 2
    assert data["variety"] == "BPT 5204"
    # BPT 5204: 2700, 2800 -> avg = 2750.0
    assert data["avg_modal_price"] == 2750.0
    print(f"  [PASS] GET /market/analytics/summary?variety=BPT 5204 -> 200 OK, total=2, avg=2750.0")
    results["filtered_variety_summary"] = "PASS"


def run_missing_and_invalid_param_tests(results: dict):
    print("\n--- PHASE 4: Missing Periods, Unmatched Filters & Parameter Validation ---")

    # 17. Unmatched filter (Non-existent variety)
    r = requests.get(f"{BASE_URL}/market/analytics/summary?variety=NonExistentVariety")
    assert r.status_code == 200
    data = r.json()
    assert data["has_data"] is False
    assert data["total_observations"] == 0
    assert data["avg_modal_price"] is None
    print(f"  [PASS] GET /market/analytics/summary?variety=NonExistentVariety -> 200 OK, has_data=False, total=0")
    results["unmatched_filter_summary"] = "PASS"

    # 18. Unmatched filter on trends
    r = requests.get(f"{BASE_URL}/market/analytics/trends?district=NonExistentDistrict")
    assert r.status_code == 200
    data = r.json()
    assert data["total_observations"] == 0
    assert data["trend_direction"] == "insufficient_data"
    print(f"  [PASS] GET /market/analytics/trends?district=NonExistentDistrict -> 200 OK, trend='insufficient_data'")
    results["unmatched_filter_trends"] = "PASS"

    # 19. Parameter Validation: days=0 -> 422
    r = requests.get(f"{BASE_URL}/market/analytics/trends?days=0")
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
    print(f"  [PASS] GET /market/analytics/trends?days=0 -> 422 Unprocessable Entity (ge=1 boundary)")
    results["invalid_days_0"] = "PASS"

    # 20. Parameter Validation: days=-5 -> 422
    r = requests.get(f"{BASE_URL}/market/analytics/trends?days=-5")
    assert r.status_code == 422
    print(f"  [PASS] GET /market/analytics/trends?days=-5 -> 422 Unprocessable Entity (negative days rejected)")
    results["invalid_days_negative"] = "PASS"

    # 21. Parameter Validation: days=91 -> 422 (max 90)
    r = requests.get(f"{BASE_URL}/market/analytics/trends?days=91")
    assert r.status_code == 422
    print(f"  [PASS] GET /market/analytics/trends?days=91 -> 422 Unprocessable Entity (le=90 boundary)")
    results["invalid_days_91"] = "PASS"

    # 22. Parameter Validation on districts: days=0 -> 422
    r = requests.get(f"{BASE_URL}/market/analytics/districts?days=0")
    assert r.status_code == 422
    print(f"  [PASS] GET /market/analytics/districts?days=0 -> 422 Unprocessable Entity")
    results["invalid_district_days_0"] = "PASS"

    # 23. Parameter Validation on varieties: days=100 -> 422
    r = requests.get(f"{BASE_URL}/market/analytics/varieties?days=100")
    assert r.status_code == 422
    print(f"  [PASS] GET /market/analytics/varieties?days=100 -> 422 Unprocessable Entity")
    results["invalid_variety_days_100"] = "PASS"


def run_error_and_regression_tests(results: dict):
    print("\n--- PHASE 5: Database Error Handling & Existing Route Regressions ---")

    # 24. Database Error Handling: Simulate DB failure on summary
    with patch.object(MarketPriceRepository, "get_market_summary", side_effect=Exception("Simulated connection timeout")):
        r = requests.get(f"{BASE_URL}/market/analytics/summary")
        assert r.status_code == 500
        data = r.json()
        assert "internal database error occurred" in data["detail"].lower()
        # Verify no credentials leaked
        assert "password" not in data["detail"].lower()
        assert "postgresql" not in data["detail"].lower()
    print(f"  [PASS] Database error simulation on summary -> 500 Internal Server Error (sanitized)")
    results["db_error_summary"] = "PASS"

    # 25. Database Error Handling: Simulate DB failure on trends
    with patch.object(MarketPriceRepository, "get_daily_trends", side_effect=Exception("Simulated query execution error")):
        r = requests.get(f"{BASE_URL}/market/analytics/trends?days=7")
        assert r.status_code == 500
        data = r.json()
        assert "internal database error occurred" in data["detail"].lower()
    print(f"  [PASS] Database error simulation on trends -> 500 Internal Server Error (sanitized)")
    results["db_error_trends"] = "PASS"

    # 26. Existing Endpoint Regression: GET /market/prices
    r = requests.get(f"{BASE_URL}/market/prices")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 9
    assert len(data["items"]) == 9
    print(f"  [PASS] Regression: GET /market/prices -> 200 OK, total={data['total']}")
    results["regression_market_prices"] = "PASS"

    # 27. Existing Endpoint Regression: GET /market/prices/latest
    r = requests.get(f"{BASE_URL}/market/prices/latest?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 5
    assert data["items"][0]["price_date"] >= data["items"][1]["price_date"]
    print(f"  [PASS] Regression: GET /market/prices/latest -> 200 OK, {len(data['items'])} items returned")
    results["regression_market_prices_latest"] = "PASS"

    # 28. Existing Endpoint Regression: POST /market/sync (unconfigured key -> 503)
    r = requests.post(f"{BASE_URL}/market/sync")
    assert r.status_code == 503
    assert "api key is not configured" in r.json()["detail"].lower()
    print(f"  [PASS] Regression: POST /market/sync -> 503 Service Unavailable (missing key guard)")
    results["regression_market_sync"] = "PASS"

    # 29. Existing System Route Regression: GET /health
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
    print(f"  [PASS] Regression: GET /health -> 200 OK (service healthy)")
    results["regression_health"] = "PASS"


def main():
    print("=" * 80)
    print("STEP 11G.4 — MANDI PRICE ANALYTICS & TREND AGGREGATIONS TEST SUITE")
    print("=" * 80)

    # 0. Clean any leftover test records before asserting baseline
    asyncio.run(cleanup_test_market_data())
    reset_db_singletons()

    # 1. Baseline verification
    f_cnt, s_cnt, mp_cnt, b_cnt = asyncio.run(get_db_counts())
    reset_db_singletons()

    print(f"Pre-test Database Row Counts:")
    print(f"  fields:                 {f_cnt} (must be 58)")
    print(f"  satellite_observations: {s_cnt} (must be 580)")
    print(f"  market_prices:          {mp_cnt} (must be 0)")
    print(f"  buyers:                 {b_cnt} (must be 0)")

    assert f_cnt == 58, f"Fields contaminated: {f_cnt}"
    assert s_cnt == 580, f"Satellite observations contaminated: {s_cnt}"
    assert mp_cnt == 0, f"Market prices baseline not 0: {mp_cnt}"
    assert b_cnt == 0, f"Buyers baseline not 0: {b_cnt}"

    results = {}

    # Start single test server instance
    print("\n[Setup] Starting test server for Mandi Price Analytics...")
    server = ServerThread(port=PORT)
    server.start()
    assert wait_for_server(BASE_URL), f"Test server failed to start on port {PORT}"
    print("  [OK] Test server online.")

    try:
        # Phase 1: Empty database tests
        run_empty_db_tests(results)

        # Phase 2: Single observation tests
        print("\n[Transition] Seeding single isolated market observation...")
        asyncio.run(seed_single_observation())
        run_single_observation_tests(results)

        # Phase 3: Multi-observation dataset tests
        print("\n[Transition] Cleaning single observation and seeding multi-date dataset (9 records)...")
        asyncio.run(cleanup_test_market_data())
        asyncio.run(seed_multi_observations())
        run_multi_observation_tests(results)
        run_missing_and_invalid_param_tests(results)
        run_error_and_regression_tests(results)

    finally:
        server.stop()
        server.join(timeout=5.0)
        print("  [OK] Test server stopped.")

    # Cleanup and verify final baseline
    print("\n[Teardown] Cleaning up all test data...")
    asyncio.run(cleanup_test_market_data())

    final_f, final_s, final_mp, final_b = asyncio.run(get_db_counts())
    reset_db_singletons()

    print(f"\nPost-test Database Row Counts:")
    print(f"  fields:                 {final_f} (must be 58)")
    print(f"  satellite_observations: {final_s} (must be 580)")
    print(f"  market_prices:          {final_mp} (must be 0)")
    print(f"  buyers:                 {final_b} (must be 0)")

    assert final_f == 58, "Fields altered!"
    assert final_s == 580, "Satellite observations altered!"
    assert final_mp == 0, f"market_prices not cleaned up: {final_mp}"
    assert final_b == 0, f"buyers altered: {final_b}"

    print("\n" + "=" * 80)
    print(f"ALL STEP 11G.4 TESTS PASSED ({len(results)}/{len(results)}) (100% PASS)")
    print("=" * 80)
    return results


if __name__ == "__main__":
    main()
