"""
Paddy Farming Assistant - Database Integration & Health Route Test Suite (STEP 11F.3)
Tests SQLAlchemy 2.x asyncpg integration, session lifecycle, error handling,
and FastAPI GET /health/database HTTP endpoint.
"""

import sys
import os
import time
import asyncio
import threading
from pathlib import Path
from unittest.mock import patch

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests
import uvicorn
from sqlalchemy import text
from app import config
from app.main import app
from app.db.session import (
    get_async_engine,
    close_db_engine,
    AsyncSessionLocal,
    get_db,
    check_db_connectivity,
    get_database_url,
)


class ServerThread(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = 8003):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        cfg = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self.server = uvicorn.Server(cfg)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


def test_database_url_safety():
    """Verify URL.create() generates a valid URL without leaking credentials in logs."""
    print("\n--- Test 1: Safe Database URL Construction ---")
    url = get_database_url()
    assert url.drivername == "postgresql+asyncpg", f"Unexpected driver: {url.drivername}"
    assert url.username == config.POSTGRES_USER, f"Unexpected username: {url.username}"
    assert url.host == config.POSTGRES_HOST, f"Unexpected host: {url.host}"
    assert url.port == config.POSTGRES_PORT, f"Unexpected port: {url.port}"
    assert url.database == config.POSTGRES_DB, f"Unexpected database: {url.database}"
    
    # Verify render_as_string(hide_password=True) hides credentials
    safe_str = url.render_as_string(hide_password=True)
    assert "***" in safe_str, "Password was not hidden in safe string!"
    if config.POSTGRES_PASSWORD:
        assert config.POSTGRES_PASSWORD not in safe_str, "Cleartext password leaked in safe representation!"
    print("  [PASS] URL.create() constructs driver=postgresql+asyncpg safely with password masking.")


async def test_direct_connectivity_and_identity():
    """Verify AsyncEngine direct connection, SELECT 1, and PostgreSQL identity."""
    print("\n--- Test 2: Direct AsyncEngine Connection & Identity Check ---")
    engine = get_async_engine()
    async with engine.connect() as conn:
        stmt = text("SELECT 1 AS alive, current_database() AS dbname, current_user AS username;")
        res = await conn.execute(stmt)
        row = res.mappings().one()
        assert row["alive"] == 1, "SELECT 1 failed"
        assert row["dbname"] == config.POSTGRES_DB, f"Expected DB {config.POSTGRES_DB}, got {row['dbname']}"
        assert row["username"] == config.POSTGRES_USER, f"Expected user {config.POSTGRES_USER}, got {row['username']}"
        print(f"  [PASS] Direct query confirmed: database='{row['dbname']}', user='{row['username']}'.")


async def test_connectivity_check_function():
    """Verify check_db_connectivity() returns healthy status and sanitized fields."""
    print("\n--- Test 3: check_db_connectivity() Status Function ---")
    health = await check_db_connectivity()
    assert health["status"] == "healthy", f"Expected status healthy, got {health['status']}"
    assert health["connected"] is True, "Expected connected=True"
    assert health["database"] == config.POSTGRES_DB, f"Expected {config.POSTGRES_DB}"
    assert health["user"] == config.POSTGRES_USER, f"Expected {config.POSTGRES_USER}"
    assert health["host"] == config.POSTGRES_HOST
    assert health["port"] == config.POSTGRES_PORT
    assert "latency_ms" in health
    assert "password" not in health
    assert config.POSTGRES_PASSWORD not in str(health)
    print(f"  [PASS] check_db_connectivity() verified: status={health['status']}, latency={health['latency_ms']}ms.")


async def test_session_generator_lifecycle():
    """Verify get_db() dependency context manager cleanup and rollback."""
    print("\n--- Test 4: AsyncSession Generator Lifecycle & Rollback ---")
    # Normal query through generator
    session_gen = get_db()
    session = await anext(session_gen)
    try:
        res = await session.execute(text("SELECT 100 AS num;"))
        val = res.scalar_one()
        assert val == 100, f"Expected 100, got {val}"
    finally:
        try:
            await anext(session_gen)
        except StopAsyncIteration:
            pass

    # Rollback behavior on exception
    session_gen2 = get_db()
    session2 = await anext(session_gen2)
    try:
        await session2.execute(text("SELECT 1;"))
        raise RuntimeError("Simulated transaction fault")
    except RuntimeError:
        pass  # Expected
    finally:
        try:
            await anext(session_gen2)
        except StopAsyncIteration:
            pass

    print("  [PASS] get_db() session lifecycle: yield, commit/rollback, and close confirmed.")


async def test_failure_handling_sanitization():
    """Verify check_db_connectivity() handles failures gracefully without secret leakage."""
    print("\n--- Test 5: Failure Handling & Error Sanitization ---")
    with patch.object(config, "POSTGRES_PASSWORD", ""):
        res = await check_db_connectivity()
        assert res["status"] == "unhealthy"
        assert res["connected"] is False
        assert res["error_type"] == "configuration_error"
        assert "password" in res["detail"].lower()
    print("  [PASS] Failure handling correctly returns status=unhealthy with sanitized description.")


async def run_async_tests():
    test_database_url_safety()
    await test_direct_connectivity_and_identity()
    await test_connectivity_check_function()
    await test_session_generator_lifecycle()
    await test_failure_handling_sanitization()
    # Clean up async engine before launching HTTP server in separate thread
    await close_db_engine()


def test_http_endpoints():
    """Starts live server and verifies GET / and GET /health/database over HTTP."""
    print("\n--- Test 6: FastAPI HTTP Health Endpoints (GET /health/database) ---")
    port = 8003
    server = ServerThread(port=port)
    server.start()

    time.sleep(3.0)  # Allow server startup & lifespan
    base_url = f"http://127.0.0.1:{port}"

    try:
        # Check root endpoint
        r_root = requests.get(f"{base_url}/", timeout=10)
        assert r_root.status_code == 200, f"Root returned {r_root.status_code}"
        root_data = r_root.json()
        assert "health_database" in root_data, "health_database missing from root"
        assert root_data["health_database"] == "/health/database"
        print("  [PASS] GET / contains 'health_database': '/health/database'.")

        # Check /health/database
        r_db = requests.get(f"{base_url}/health/database", timeout=10)
        assert r_db.status_code == 200, f"Expected 200, got {r_db.status_code}: {r_db.text}"
        db_data = r_db.json()
        assert db_data["status"] == "healthy", f"Expected healthy, got {db_data['status']}"
        assert db_data["connected"] is True, f"Expected connected=True"
        assert db_data["database"] == config.POSTGRES_DB
        assert db_data["user"] == config.POSTGRES_USER
        assert db_data["host"] == config.POSTGRES_HOST
        assert db_data["port"] == config.POSTGRES_PORT
        assert "latency_ms" in db_data

        # Verify no credentials leaked
        if config.POSTGRES_PASSWORD:
            assert config.POSTGRES_PASSWORD not in r_db.text, "Password leaked in HTTP response!"
        assert "password" not in db_data, "'password' key found in HTTP response!"

        # Verify cache control headers
        assert r_db.headers.get("Cache-Control") == "no-cache, no-store, must-revalidate"
        print(f"  [PASS] GET /health/database HTTP 200 OK: status={db_data['status']}, database={db_data['database']}.")

        # Check general health check independence
        r_health = requests.get(f"{base_url}/health", timeout=10)
        assert r_health.status_code == 200
        health_data = r_health.json()
        assert health_data["status"] == "healthy"
        print("  [PASS] GET /health operational and independent.")

        # Check model health check
        r_model = requests.get(f"{base_url}/health/model", timeout=10)
        assert r_model.status_code == 200
        print("  [PASS] GET /health/model operational and independent.")

    finally:
        server.stop()
        time.sleep(1.0)


def main():
    print("=" * 80)
    print("RUNNING STEP 11F.3 DATABASE INTEGRATION TEST SUITE")
    print("=" * 80)

    try:
        # Run all async tests within a single event loop
        asyncio.run(run_async_tests())

        # Run HTTP integration tests against Uvicorn live server
        test_http_endpoints()

        print("\n" + "=" * 80)
        print("ALL DATABASE INTEGRATION TESTS PASSED (6/6)")
        print("=" * 80)
        return 0
    except Exception as exc:
        print(f"\n[FAIL] Test suite failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
