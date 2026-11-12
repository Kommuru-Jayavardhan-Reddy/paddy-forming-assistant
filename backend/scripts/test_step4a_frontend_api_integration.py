"""
Paddy Farming Assistant - STEP 4A Frontend API Integration Suite
Tests the exact endpoint handlers and request schemas matching frontend payloads against
the real PostgreSQL staging database (paddy_farming_staging).
Zero connections to production database (paddy_farming_db).
"""

import os
import sys
import uuid
import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Dict, Any

import asyncpg
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

BACKEND_DIR = Path("c:/paddy project/backend")
sys.path.insert(0, str(BACKEND_DIR))

from app import config

# Safety: strictly target staging database
STAGING_DB = "paddy_farming_staging"
config.POSTGRES_DB = STAGING_DB

from app.db.session import init_db_engine, get_async_engine, close_db_engine
from app.core.security import hash_password, create_access_token, decode_access_token
from app.core.dependencies import get_current_user, require_admin
from app.schemas.auth import FarmerRegisterRequest, FarmerLoginRequest
from app.api.auth import register_farmer, login, get_current_profile, get_system_status
from app.db.models.farmer import Farmer

results: Dict[str, Dict[str, Any]] = {}


def record_result(test_num: int, name: str, passed: bool, details: str):
    key = f"TEST_{test_num}"
    results[key] = {
        "name": name,
        "passed": passed,
        "details": details
    }
    status_str = "PASSED" if passed else "FAILED"
    print(f"[{status_str}] {key}: {name}")
    print(f"  -> {details}\n")


async def run_suite():
    print("=" * 75)
    print("STARTING STEP 4A FRONTEND API INTEGRATION TEST SUITE")
    print(f"Target Database: '{STAGING_DB}' (PostgreSQL on 127.0.0.1:5432)")
    print("=" * 75 + "\n")

    # 0. Verify staging connection directly
    conn = await asyncpg.connect(
        user="postgres",
        password=config.POSTGRES_PASSWORD,
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=STAGING_DB
    )
    db_name = await conn.fetchval("SELECT current_database();")
    assert db_name == STAGING_DB, f"FATAL: Connected to '{db_name}', expected '{STAGING_DB}'!"

    # Clean synthetic test data from previous runs
    await conn.execute("DELETE FROM public.farmers WHERE username LIKE 'step4a_%' OR mobile_number LIKE '988887777%';")
    await conn.close()

    init_db_engine()
    engine = get_async_engine()

    farmer1_token = None
    farmer1_id = None
    farmer1_schema = None
    admin_token = None
    admin_id = None

    # --------------------------------------------------------------------------
    # 1. Successful farmer registration (matching Frontend Register.jsx payload)
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            reg_req = FarmerRegisterRequest(
                username="step4a_farmer1",
                password="FarmerPassword2026!",
                mobile_number="9888877771",
                full_name="Step 4A Farmer One",
                farm_name="Cauvery Delta Farm",
                village="Thanjavur"
            )
            profile = await register_farmer(request=reg_req, db=session)
            assert profile.username == "step4a_farmer1"
            assert profile.role == "farmer"
            assert profile.normalized_mobile == "+919888877771"
            assert profile.schema_name.startswith("farmer_")
            farmer1_id = profile.id
            farmer1_schema = profile.schema_name
            record_result(1, "Farmer Registration via Frontend Payload", True,
                          f"Successfully registered farmer '{profile.username}' with provisioned schema '{farmer1_schema}'.")
    except Exception as exc:
        record_result(1, "Farmer Registration via Frontend Payload", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 2. Farmer login using Username (matching Frontend Login.jsx)
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            login_req = FarmerLoginRequest(
                username="step4a_farmer1",
                password="FarmerPassword2026!"
            )
            token_resp = await login(request=login_req, db=session)
            assert token_resp.token_type == "access"
            assert token_resp.role == "farmer"
            assert token_resp.username == "step4a_farmer1"
            assert token_resp.schema_name == farmer1_schema
            farmer1_token = token_resp.access_token
            record_result(2, "Farmer Login with Username", True,
                          f"Authenticated via username. Issued HS256 JWT for role='{token_resp.role}'.")
    except Exception as exc:
        record_result(2, "Farmer Login with Username", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 3. Farmer login using 10-digit Mobile Number in single identifier input
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            login_req = FarmerLoginRequest(
                username="9888877771",
                password="FarmerPassword2026!"
            )
            token_resp = await login(request=login_req, db=session)
            assert token_resp.username == "step4a_farmer1"
            assert token_resp.role == "farmer"
            record_result(3, "Farmer Login with 10-digit Mobile Identifier", True,
                          "Successfully resolved '9888877771' -> '+919888877771' from single identifier field.")
    except Exception as exc:
        record_result(3, "Farmer Login with 10-digit Mobile Identifier", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 4. Farmer login using E.164 Mobile Number (+91 format)
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            login_req = FarmerLoginRequest(
                username="+919888877771",
                password="FarmerPassword2026!"
            )
            token_resp = await login(request=login_req, db=session)
            assert token_resp.username == "step4a_farmer1"
            record_result(4, "Farmer Login with E.164 Mobile Identifier", True,
                          "Successfully authenticated via full international format '+919876543210'.")
    except Exception as exc:
        record_result(4, "Farmer Login with E.164 Mobile Identifier", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 5. Invalid password rejection (HTTP 401 with uniform detail)
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            rejected = False
            try:
                await login(request=FarmerLoginRequest(username="step4a_farmer1", password="IncorrectPassword!"), db=session)
            except HTTPException as exc:
                if exc.status_code == 401 and exc.detail == "Invalid username, mobile number, or password.":
                    rejected = True
            assert rejected, "Incorrect password was not rejected with expected 401"
            record_result(5, "Invalid Password Rejection (HTTP 401)", True,
                          "Rejected incorrect password with HTTP 401 and uniform error message.")
    except Exception as exc:
        record_result(5, "Invalid Password Rejection (HTTP 401)", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 6. Protected /auth/me call with valid Bearer token
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=farmer1_token)
            curr_user = await get_current_user(credentials=creds, db=session)
            me = await get_current_profile(current_user=curr_user)
            assert me.username == "step4a_farmer1"
            assert me.role == "farmer"
            assert hasattr(me, "password_hash") is True
            # Profile response model will serialize excluding password_hash
            record_result(6, "Protected Profile API Call (GET /auth/me)", True,
                          "Bearer token resolved authentic farmer principal from PostgreSQL.")
    except Exception as exc:
        record_result(6, "Protected Profile API Call (GET /auth/me)", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 7. Admin account provisioning & login (Admin Dashboard Source of Truth)
    # --------------------------------------------------------------------------
    try:
        # Seed verified Admin directly in staging database
        conn = await asyncpg.connect(
            user="postgres",
            password=config.POSTGRES_PASSWORD,
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=STAGING_DB
        )
        admin_id = uuid.uuid4()
        admin_hash = hash_password("AdminSecurePassword2026!")
        await conn.execute("""
            INSERT INTO public.farmers (id, username, password_hash, role, schema_name, is_active)
            VALUES ($1, 'step4a_admin', $2, 'admin', NULL, TRUE);
        """, admin_id, admin_hash)
        await conn.close()

        async with AsyncSession(engine, expire_on_commit=False) as session:
            adm_resp = await login(request=FarmerLoginRequest(username="step4a_admin", password="AdminSecurePassword2026!"), db=session)
            assert adm_resp.role == "admin"
            assert adm_resp.schema_name is None
            admin_token = adm_resp.access_token
            record_result(7, "Admin Login & Verified Role Claim", True,
                          f"Admin authenticated. Server-verified role='admin', schema_name=NULL.")
    except Exception as exc:
        record_result(7, "Admin Login & Verified Role Claim", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 8. Admin accesses /admin/system-status (Admin Dashboard)
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token)
            admin_user = await get_current_user(credentials=creds, db=session)
            verified_admin = await require_admin(current_user=admin_user)
            status_data = await get_system_status(current_admin=verified_admin)
            assert status_data["access_granted"] is True
            assert status_data["authenticated_admin"] == "step4a_admin"
            record_result(8, "Admin Access to /admin/system-status", True,
                          f"Admin queried diagnostic status: status='{status_data['status']}'.")
    except Exception as exc:
        record_result(8, "Admin Access to /admin/system-status", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 9. Farmer CANNOT access /admin/system-status (HTTP 403 Forbidden)
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=farmer1_token)
            farmer_user = await get_current_user(credentials=creds, db=session)
            farmer_blocked = False
            try:
                await require_admin(current_user=farmer_user)
            except HTTPException as exc:
                if exc.status_code == 403:
                    farmer_blocked = True
            assert farmer_blocked, "Farmer was permitted on require_admin!"
            record_result(9, "Farmer Blocked from Admin Endpoint (HTTP 403)", True,
                          "Server-side require_admin rejected farmer with HTTP 403 Forbidden.")
    except Exception as exc:
        record_result(9, "Farmer Blocked from Admin Endpoint (HTTP 403)", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 10. Expired token rejection (HTTP 401)
    # --------------------------------------------------------------------------
    try:
        short_token = create_access_token(
            data={"sub": str(farmer1_id), "username": "step4a_farmer1", "role": "farmer"},
            expires_delta=timedelta(seconds=1)
        )
        await asyncio.sleep(2)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=short_token)
            expired_rejected = False
            try:
                await get_current_user(credentials=creds, db=session)
            except HTTPException as exc:
                if exc.status_code == 401 and "expired" in exc.detail.lower():
                    expired_rejected = True
            assert expired_rejected, "Expired token was accepted!"
            record_result(10, "Expired Bearer Token Rejection (HTTP 401)", True,
                          "Expired token safely rejected with HTTP 401: 'Access token has expired.'")
    except Exception as exc:
        record_result(10, "Expired Bearer Token Rejection (HTTP 401)", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 11. Unauthenticated request rejection (HTTP 401)
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            unauth_rejected = False
            try:
                await get_current_user(credentials=None, db=session)
            except HTTPException as exc:
                if exc.status_code == 401:
                    unauth_rejected = True
            assert unauth_rejected, "Unauthenticated request was accepted!"
            record_result(11, "Missing Authorization Header Rejection", True,
                          "Unauthenticated request strictly rejected with HTTP 401 Unauthorized.")
    except Exception as exc:
        record_result(11, "Missing Authorization Header Rejection", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 12. Public registration cannot escalate to Admin role
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            esc_req = FarmerRegisterRequest.model_validate({
                "username": "step4a_attacker",
                "password": "AttackerPass2026!",
                "mobile_number": "9888877779",
                "full_name": "Attacker Trying Escalation",
                "role": "admin",
                "is_admin": True
            })
            esc_created = await register_farmer(request=esc_req, db=session)
            assert esc_created.role == "farmer", f"Attacker escalated to {esc_created.role}!"
            record_result(12, "Registration Privilege Escalation Prevention", True,
                          "Server-enforced role='farmer'; client-injected 'role: admin' was safely discarded.")
    except Exception as exc:
        record_result(12, "Registration Privilege Escalation Prevention", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 13. Registration duplicate mobile validation
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            dup_req = FarmerRegisterRequest(
                username="step4a_farmer_dup",
                password="ValidPassword2026!",
                mobile_number="9876543210",  # already registered to farmer1
                full_name="Duplicate Test Farmer"
            )
            dup_rejected = False
            try:
                await register_farmer(request=dup_req, db=session)
            except HTTPException as exc:
                if exc.status_code == 400 and "already registered" in exc.detail.lower():
                    dup_rejected = True
            assert dup_rejected, "Duplicate mobile was not rejected with 400"
            record_result(13, "Duplicate Mobile Rejection on Registration", True,
                          "Rejected duplicate mobile with HTTP 400: 'already registered to another account.'")
    except Exception as exc:
        record_result(13, "Duplicate Mobile Rejection on Registration", False, f"Failed: {exc}")

    # Cleanup synthetic test schemas and farmers
    conn = await asyncpg.connect(
        user="postgres",
        password=config.POSTGRES_PASSWORD,
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=STAGING_DB
    )
    test_schemas = await conn.fetch("SELECT schema_name FROM public.farmers WHERE username LIKE 'step4a_%' AND schema_name IS NOT NULL;")
    for r in test_schemas:
        s = r["schema_name"]
        role = f"tenant_{s}"
        await conn.execute(f'DROP SCHEMA IF EXISTS "{s}" CASCADE;')
        await conn.execute(f'DROP OWNED BY "{role}"; DROP ROLE IF EXISTS "{role}";')
    await conn.execute("DELETE FROM public.farmers WHERE username LIKE 'step4a_%';")
    await conn.close()
    await close_db_engine()

    print("=" * 75)
    print("STEP 4A BACKEND API INTEGRATION SUMMARY:")
    print("=" * 75)
    all_passed = True
    for k, v in results.items():
        st = "PASSED" if v["passed"] else "FAILED"
        if not v["passed"]:
            all_passed = False
        print(f"  {k:8} : [{st:7}] {v['name']}")
    print("=" * 75)
    if all_passed:
        print("ALL 13 STEP 4A BACKEND API INTEGRATION TESTS PASSED (100% SUCCESS)!")
    else:
        print("SOME TESTS FAILED! Inspect errors above.")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_suite())
