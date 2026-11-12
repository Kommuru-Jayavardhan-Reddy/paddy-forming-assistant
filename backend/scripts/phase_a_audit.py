"""
Paddy Farming Assistant - Phase A Pre-Implementation Audit (STEP 11F.8)
Inspects database connectivity, actual table row counts for all seven tables,
and inspects the active backend state.
"""

import sys
import asyncio
from pathlib import Path
from sqlalchemy import text

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import AsyncSessionLocal, check_db_connectivity, close_db_engine


async def run_phase_a_audit():
    print("=" * 70)
    print("STEP 11F.8 — PHASE A: PRE-IMPLEMENTATION AUDIT")
    print("=" * 70)

    # 1. Database Connection Check
    health = await check_db_connectivity()
    print("\n1. Database Connection Status:")
    for k, v in health.items():
        print(f"   {k}: {v}")

    if not health.get("connected"):
        print("[FAIL] Database is not connected.")
        return False

    # 2. Query Row Counts for all 7 application tables
    tables = [
        "fields",
        "satellite_observations",
        "prediction_history",
        "weather_records",
        "market_prices",
        "buyers",
        "reports",
    ]

    print("\n2. Actual PostgreSQL Row Counts:")
    counts = {}
    try:
        async with AsyncSessionLocal() as session:
            for tbl in tables:
                res = await session.execute(text(f"SELECT count(*) FROM {tbl}"))
                cnt = res.scalar()
                counts[tbl] = cnt
                print(f"   - {tbl:<25}: {cnt:>5} records")

            # Check Alembic version
            res_alembic = await session.execute(text("SELECT version_num FROM alembic_version"))
            version_num = res_alembic.scalar()
            print(f"\n3. Alembic Current Revision:")
            print(f"   version_num: {version_num}")
    finally:
        await close_db_engine()

    print("\n" + "=" * 70)
    print("PHASE A AUDIT COMPLETED SUCCESSFULLY")
    print("=" * 70)
    return True


if __name__ == "__main__":
    asyncio.run(run_phase_a_audit())
