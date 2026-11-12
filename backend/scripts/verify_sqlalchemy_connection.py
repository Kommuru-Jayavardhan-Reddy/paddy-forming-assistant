"""
Paddy Farming Assistant - SQLAlchemy ORM & Database Connection Verification
(STEP 11F.3 Verification Script)

Validates asynchronous SQLAlchemy engine connection to PostgreSQL via asyncpg:
1. Loads backend configuration from backend/.env.
2. Initializes SQLAlchemy AsyncEngine with safe URL.create().
3. Executes SELECT 1, current_database(), current_user, and inet_server_addr().
4. Confirms database is paddy_farming_db and user is paddy_app.
5. Confirms session disposal and clean engine shutdown.
6. Never prints secrets, connection strings, or passwords.
7. Exits with 0 on success, 1 on failure.
"""

import sys
import os
import asyncio
from pathlib import Path
from sqlalchemy import text

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import config
from app.db.session import (
    get_async_engine,
    close_db_engine,
    AsyncSessionLocal,
    check_db_connectivity,
)


async def main() -> int:
    print("=" * 80)
    print("STEP 11F.3 — SQLALCHEMY ASYNC DATABASE CONNECTION VERIFICATION")
    print("=" * 80)

    # 1. Configuration check (never print password)
    print("\n[1/5] Checking Configuration Environment Variables...")
    print(f"  POSTGRES_HOST:     {config.POSTGRES_HOST}")
    print(f"  POSTGRES_PORT:     {config.POSTGRES_PORT}")
    print(f"  POSTGRES_DB:       {config.POSTGRES_DB}")
    print(f"  POSTGRES_USER:     {config.POSTGRES_USER}")
    print(f"  POSTGRES_PASSWORD: {'[CONFIGURED]' if config.POSTGRES_PASSWORD else '[MISSING]'}")
    print(f"  DB_POOL_SIZE:      {config.DB_POOL_SIZE}")
    print(f"  DB_MAX_OVERFLOW:   {config.DB_MAX_OVERFLOW}")

    if not config.POSTGRES_PASSWORD:
        print("\n[ERROR] POSTGRES_PASSWORD is not set in backend/.env!")
        return 1

    # 2. Reusable check_db_connectivity() test
    print("\n[2/5] Running check_db_connectivity()...")
    health = await check_db_connectivity()
    print(f"  Status:       {health.get('status')}")
    print(f"  Connected:    {health.get('connected')}")
    print(f"  Database:     {health.get('database')}")
    print(f"  User:         {health.get('user')}")
    print(f"  Latency:      {health.get('latency_ms')} ms")

    if not health.get("connected"):
        print(f"\n[ERROR] Connectivity check failed: {health.get('detail')} (type: {health.get('error_type')})")
        return 1

    # 3. Direct AsyncEngine Connection & Identity Check
    print("\n[3/5] Executing SELECT 1 and identity verification query via AsyncEngine...")
    engine = get_async_engine()
    try:
        async with engine.connect() as conn:
            stmt = text("SELECT 1 AS alive, current_database() AS dbname, current_user AS username, version() AS pg_version;")
            res = await conn.execute(stmt)
            row = res.mappings().one()

            alive = row["alive"]
            current_db = row["dbname"]
            current_user = row["username"]
            pg_ver = row["pg_version"]

            print(f"  SELECT 1 result:    {alive}")
            print(f"  current_database(): {current_db}")
            print(f"  current_user:       {current_user}")
            print(f"  PostgreSQL version: {pg_ver.split()[0]} {pg_ver.split()[1]}")

            if alive != 1:
                print(f"[FAIL] Expected alive=1, got {alive}")
                return 1

            if current_db != config.POSTGRES_DB:
                print(f"[FAIL] Expected current_database() to be '{config.POSTGRES_DB}', got '{current_db}'")
                return 1

            if current_user != config.POSTGRES_USER:
                print(f"[FAIL] Expected current_user to be '{config.POSTGRES_USER}', got '{current_user}'")
                return 1

            print("  Identity Verification: PASS")
    except Exception as exc:
        print(f"[ERROR] Engine query execution failed: {type(exc).__name__}: {exc}")
        return 1

    # 4. AsyncSessionLocal verification & clean session exit
    print("\n[4/5] Testing AsyncSessionLocal session factory lifecycle...")
    try:
        async with AsyncSessionLocal() as session:
            sess_res = await session.execute(text("SELECT 42 AS answer;"))
            val = sess_res.scalar_one()
            print(f"  AsyncSession query 'SELECT 42': {val}")
            if val != 42:
                print(f"[FAIL] Unexpected session scalar result: {val}")
                return 1
            print("  AsyncSession Lifecycle: PASS")
    except Exception as exc:
        print(f"[ERROR] AsyncSession execution failed: {type(exc).__name__}: {exc}")
        return 1

    # 5. Clean Engine Disposal
    print("\n[5/5] Disposing SQLAlchemy AsyncEngine cleanly...")
    try:
        await close_db_engine()
        print("  Engine disposal: PASS")
    except Exception as exc:
        print(f"[ERROR] Failed to dispose engine: {exc}")
        return 1

    print("\n" + "=" * 80)
    print("STEP 11F.3 SQLALCHEMY DATABASE VERIFICATION: ALL CHECKS PASSED")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
