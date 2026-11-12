"""
Paddy Farming Assistant - Pre-Migration Database Inspection (STEP 11F.6)
Connects to PostgreSQL paddy_farming_db, queries catalogs for existing tables,
schemas, constraints, and verifies ORM metadata before migration.
"""

import sys
import asyncio
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text
from app import config
from app.db.base import Base
import app.db.models  # Imports all 7 models into Base.metadata
from app.db.session import get_async_engine, close_db_engine


async def inspect_database() -> dict:
    print("=" * 80)
    print("STEP 11F.6 — PRE-MIGRATION DATABASE INSPECTION")
    print("=" * 80)

    # 1. Environment / Target Check
    print("\n[1/4] Target Configuration:")
    print(f"  Target Database: {config.POSTGRES_DB}")
    print(f"  Target User:     {config.POSTGRES_USER}")
    print(f"  Host:            {config.POSTGRES_HOST}")
    print(f"  Port:            {config.POSTGRES_PORT}")
    print(f"  Password:        {'[CONFIGURED]' if config.POSTGRES_PASSWORD else '[MISSING]'}")

    if config.POSTGRES_DB != "paddy_farming_db":
        raise ValueError(f"Unexpected target database: {config.POSTGRES_DB}")

    # 2. Metadata Tables Check
    print("\n[2/4] ORM Base.metadata Tables Registered:")
    registered_tables = sorted(list(Base.metadata.tables.keys()))
    for tbl in registered_tables:
        cols = [c.name for c in Base.metadata.tables[tbl].columns]
        print(f"  - {tbl} ({len(cols)} columns: {', '.join(cols[:5])}...)")

    expected_tables = {
        "fields",
        "prediction_history",
        "satellite_observations",
        "weather_records",
        "market_prices",
        "buyers",
        "reports",
    }
    if set(registered_tables) != expected_tables:
        raise ValueError(f"Metadata table mismatch: {expected_tables.symmetric_difference(set(registered_tables))}")
    print(f"  [PASS] All 7 target tables registered in ORM Base.metadata.")

    # 3. Live PostgreSQL Catalog Queries
    print("\n[3/4] Live Database Catalog Queries...")
    engine = get_async_engine()
    results = {}

    try:
        async with engine.connect() as conn:
            # Identity
            id_query = text("SELECT current_database() AS dbname, current_user AS username, version() AS ver;")
            id_row = (await conn.execute(id_query)).mappings().one()
            results["database"] = id_row["dbname"]
            results["user"] = id_row["username"]
            results["version"] = id_row["ver"].split()[0] + " " + id_row["ver"].split()[1]

            print(f"  Connected to Database: {results['database']}")
            print(f"  Active Session User:   {results['user']}")
            print(f"  PostgreSQL Version:    {results['version']}")

            # Check public schema tables
            tbl_query = text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name;"
            )
            tables = (await conn.execute(tbl_query)).scalars().all()
            results["existing_tables"] = tables
            print(f"  Existing tables in 'public' schema: {tables}")

            # Check if alembic_version exists
            has_alembic = "alembic_version" in tables
            results["has_alembic"] = has_alembic
            if has_alembic:
                rev_query = text("SELECT version_num FROM alembic_version;")
                revisions = (await conn.execute(rev_query)).scalars().all()
                results["existing_revisions"] = revisions
                print(f"  Existing alembic revision: {revisions}")
            else:
                results["existing_revisions"] = []
                print("  Alembic version table: NOT PRESENT (Clean database)")

    finally:
        await close_db_engine()

    print("\n[4/4] Summary:")
    print(f"  Database target confirmed as 'paddy_farming_db': {'PASS' if results['database'] == 'paddy_farming_db' else 'FAIL'}")
    print(f"  Clean initial state confirmed: {'YES' if len(results['existing_tables']) == 0 else 'NO'}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    res = asyncio.run(inspect_database())
    sys.exit(0)
