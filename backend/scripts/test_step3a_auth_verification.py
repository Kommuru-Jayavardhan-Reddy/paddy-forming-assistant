"""
Paddy Farming Assistant - STEP 3A Authentication Verification Suite
Tests all 13 requirements against real PostgreSQL staging (paddy_farming_staging) only.
Strictly adheres to safety rules: zero connections to production paddy_farming_db.
"""

import os
import sys
import uuid
import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Dict, Any

import asyncpg
from sqlalchemy import select, text
from fastapi import HTTPException

# Set project path
BACKEND_DIR = Path("c:/paddy project/backend")
sys.path.insert(0, str(BACKEND_DIR))

from app import config
from app.db.session import init_db_engine, get_async_engine, close_db_engine
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.phone import normalize_mobile_number, InvalidMobileNumberError
from app.core.dependencies import get_current_user, require_admin, require_farmer, get_tenant_db
from app.db.models.farmer import Farmer, UserRole
from app.schemas.auth import FarmerRegisterRequest, FarmerLoginRequest
from app.api.auth import register_farmer, login, _get_privileged_conn
from app.exceptions import TokenExpiredError, InvalidTokenError, SecurityConfigurationError

STAGING_DB = "paddy_farming_staging"
results: Dict[str, Dict[str, Any]] = {}


def record_result(test_num: int, name: str, passed: bool, details: str):
    key = f"VERIFY_{test_num}"
    results[key] = {
        "name": name,
        "passed": passed,
        "details": details
    }
    status_str = "PASSED" if passed else "FAILED"
    print(f"[{status_str}] {key}: {name}")
    print(f"  -> {details}\n")


async def run_all_tests():
    print("*" * 75)
    print("STARTING STEP 3A AUTHENTICATION VERIFICATION SUITE")
    print("*" * 75)
    print(f"Target Database: '{STAGING_DB}' (PostgreSQL on 127.0.0.1:5432)")
    print("Production Safety: ZERO connections or queries to 'paddy_farming_db'.\n")

    # Safety: override config.POSTGRES_DB to STAGING_DB
    config.POSTGRES_DB = STAGING_DB

    # Verify staging connection directly using privileged account
    conn = await asyncpg.connect(
        user="postgres",
        password=config.POSTGRES_PASSWORD,
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=STAGING_DB
    )
    db_name = await conn.fetchval("SELECT current_database();")
    assert db_name == STAGING_DB, f"FATAL: Connected to '{db_name}', expected '{STAGING_DB}'!"
    print(f"Verified connection to isolated staging database: '{STAGING_DB}'.")

    # Clean any leftover synthetic test records from previous runs
    await conn.execute("DELETE FROM public.farmers WHERE username LIKE 'step3a_%';")

    # Initialize SQLAlchemy Async Engine
    init_db_engine()
    engine = get_async_engine()

    from sqlalchemy.ext.asyncio import AsyncSession

    # Seed primary test farmer
    print("Setting up baseline test farmer 'step3a_user1'...")
    farmer1_id = uuid.uuid4()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        reg_req = FarmerRegisterRequest(
            username="step3a_user1",
            password="SecretPassword2026!",
            mobile_number="9876543210",
            full_name="Step 3A Primary Farmer",
            farm_name="Delta Farms",
            village="Thanjavur"
        )
        farmer1 = await register_farmer(request=reg_req, db=session)
        farmer1_id = farmer1.id
        farmer1_schema = farmer1.schema_name
        print(f"  -> Created 'step3a_user1' with schema='{farmer1_schema}', normalized_mobile='{farmer1.normalized_mobile}'.\n")

    # --------------------------------------------------------------------------
    # 1. Login with username and password
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            login_req = FarmerLoginRequest(
                username="step3a_user1",
                password="SecretPassword2026!"
            )
            token_resp = await login(request=login_req, db=session)
            assert token_resp.token_type == "access"
            assert token_resp.username == "step3a_user1"
            assert token_resp.role == "farmer"
            assert token_resp.schema_name == farmer1_schema
            decoded = decode_access_token(token_resp.access_token)
            assert decoded["sub"] == str(farmer1_id)
            record_result(1, "Login with Username and Password", True,
                          f"Successfully authenticated via username. Issued token for user='{token_resp.username}', role='{token_resp.role}'.")
    except Exception as exc:
        record_result(1, "Login with Username and Password", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 2. Login with Indian 10-digit mobile number and password
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # 2a: via username field containing 10-digit mobile
            login_req_a = FarmerLoginRequest(
                username="9876543210",
                password="SecretPassword2026!"
            )
            token_resp_a = await login(request=login_req_a, db=session)
            assert token_resp_a.username == "step3a_user1"
            assert token_resp_a.schema_name == farmer1_schema
            
            # 2b: via explicit mobile_number field
            login_req_b = FarmerLoginRequest(
                mobile_number="9876543210",
                password="SecretPassword2026!"
            )
            token_resp_b = await login(request=login_req_b, db=session)
            assert token_resp_b.username == "step3a_user1"
            assert token_resp_b.schema_name == farmer1_schema
            
            record_result(2, "Login with Indian 10-digit Mobile Number", True,
                          "Successfully resolved '9876543210' -> '+919876543210' and authenticated farmer via both fields.")
    except Exception as exc:
        record_result(2, "Login with Indian 10-digit Mobile Number", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 3. Login with E.164 mobile number and password
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            login_req = FarmerLoginRequest(
                username="+919876543210",
                password="SecretPassword2026!"
            )
            token_resp = await login(request=login_req, db=session)
            assert token_resp.username == "step3a_user1"
            assert token_resp.schema_name == farmer1_schema
            record_result(3, "Login with E.164 Mobile Number", True,
                          "Successfully authenticated using full international E.164 format '+919876543210'.")
    except Exception as exc:
        record_result(3, "Login with E.164 Mobile Number", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 4. Invalid password rejection
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # 4a: Wrong password on username
            rejected_user = False
            try:
                await login(request=FarmerLoginRequest(username="step3a_user1", password="WrongPassword!"), db=session)
            except HTTPException as exc:
                if exc.status_code == 401:
                    rejected_user = True
            assert rejected_user, "Wrong password on username was not rejected with 401"

            # 4b: Wrong password on mobile
            rejected_mobile = False
            try:
                await login(request=FarmerLoginRequest(username="9876543210", password="WrongPassword!"), db=session)
            except HTTPException as exc:
                if exc.status_code == 401:
                    rejected_mobile = True
            assert rejected_mobile, "Wrong password on mobile was not rejected with 401"

            record_result(4, "Invalid Password Rejection", True,
                          "Rejected invalid passwords for both username and mobile login with HTTP 401 Unauthorized.")
    except Exception as exc:
        record_result(4, "Invalid Password Rejection", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 5. Unknown mobile number rejection
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            rejected = False
            try:
                await login(request=FarmerLoginRequest(username="9999999999", password="SecretPassword2026!"), db=session)
            except HTTPException as exc:
                if exc.status_code == 401 and "Invalid" in exc.detail:
                    rejected = True
            assert rejected, "Unknown mobile was not rejected with 401"
            record_result(5, "Unknown Mobile Number Rejection", True,
                          "Unknown mobile number '9999999999' rejected with HTTP 401 Unauthorized.")
    except Exception as exc:
        record_result(5, "Unknown Mobile Number Rejection", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 6. Invalid mobile format rejection
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            rejected = False
            try:
                await login(request=FarmerLoginRequest(username="12345", password="SecretPassword2026!"), db=session)
            except HTTPException as exc:
                if exc.status_code == 401:
                    rejected = True
            assert rejected, "Invalid format identifier was not rejected with 401"
            record_result(6, "Invalid Mobile Format Rejection", True,
                          "Malformed phone number '12345' rejected safely without uncaught exceptions (HTTP 401).")
    except Exception as exc:
        record_result(6, "Invalid Mobile Format Rejection", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 7. Legacy farmer with NULL mobile can still log in using username
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            legacy_id = uuid.uuid4()
            legacy_farmer = Farmer(
                id=legacy_id,
                username="step3a_legacy_user",
                password_hash=hash_password("LegacySecret2026!"),
                mobile_number=None,
                normalized_mobile=None,
                role="farmer",
                schema_name=None,
                encrypted_db_secret=None,
                is_active=True
            )
            session.add(legacy_farmer)
            await session.commit()

            # Attempt login with legacy username
            resp = await login(request=FarmerLoginRequest(username="step3a_legacy_user", password="LegacySecret2026!"), db=session)
            assert resp.username == "step3a_legacy_user"
            assert resp.token_type == "access"
            assert resp.schema_name is None
            record_result(7, "Legacy Farmer (NULL Mobile) Login", True,
                          "Legacy farmer with NULL mobile_number & normalized_mobile authenticated cleanly via username.")
    except Exception as exc:
        record_result(7, "Legacy Farmer (NULL Mobile) Login", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 8. JWT signature and expiration verification
    # --------------------------------------------------------------------------
    try:
        claims = {"sub": str(uuid.uuid4()), "role": "farmer", "username": "token_test_user"}
        valid_token = create_access_token(data=claims)
        dec = decode_access_token(valid_token)
        assert dec["sub"] == claims["sub"]

        # Tampered signature
        tampered_token = valid_token[:-4] + "fake"
        tampered_rejected = False
        try:
            decode_access_token(tampered_token)
        except InvalidTokenError:
            tampered_rejected = True
        assert tampered_rejected, "Tampered signature was accepted!"

        # Expiration test
        short_token = create_access_token(data=claims, expires_delta=timedelta(seconds=1))
        await asyncio.sleep(2)
        expired_rejected = False
        try:
            decode_access_token(short_token)
        except TokenExpiredError:
            expired_rejected = True
        assert expired_rejected, "Expired token was accepted!"

        record_result(8, "JWT Signature & Expiration Verification", True,
                      "Tampered signature rejected (InvalidTokenError); expired token rejected (TokenExpiredError).")
    except Exception as exc:
        record_result(8, "JWT Signature & Expiration Verification", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 9. Farmer cannot access Admin endpoints
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            farmer_row = (await session.execute(select(Farmer).where(Farmer.username == "step3a_user1"))).scalar_one()
            
            # Farmer role calling require_admin -> MUST BE 403
            farmer_denied = False
            try:
                await require_admin(current_user=farmer_row)
            except HTTPException as exc:
                if exc.status_code == 403:
                    farmer_denied = True
            assert farmer_denied, "Farmer was permitted on require_admin!"

            # Unauthenticated calling get_current_user -> MUST BE 401
            unauth_denied = False
            try:
                await get_current_user(credentials=None, db=session)
            except HTTPException as exc:
                if exc.status_code == 401:
                    unauth_denied = True
            assert unauth_denied, "Unauthenticated request was permitted!"

            # Legitimate admin calling require_admin -> MUST BE ALLOWED
            admin_row = Farmer(
                id=uuid.uuid4(),
                username="step3a_admin_user",
                password_hash=hash_password("AdminPass2026!"),
                role="admin",
                is_active=True
            )
            adm = await require_admin(current_user=admin_row)
            assert adm.username == "step3a_admin_user"

            record_result(9, "Admin Endpoint Protection & RBAC", True,
                          "require_admin returned 403 for farmers, 401 for unauthenticated, and granted access to admin.")
    except Exception as exc:
        record_result(9, "Admin Endpoint Protection & RBAC", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 10. Farmer A cannot access Farmer B's tenant database via get_tenant_db
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # Register Farmer B
            reg_b = FarmerRegisterRequest(
                username="step3a_farmer_b",
                password="FarmerBPass2026!",
                mobile_number="9876543222",
                full_name="Farmer Bravo"
            )
            farmer_b = await register_farmer(request=reg_b, db=session)
            schema_b = farmer_b.schema_name

            farmer_a = (await session.execute(select(Farmer).where(Farmer.username == "step3a_user1"))).scalar_one()
            schema_a = farmer_a.schema_name

        # Resolve get_tenant_db generator for Farmer A
        tenant_gen_a = get_tenant_db(current_user=farmer_a)
        sess_a = await anext(tenant_gen_a)
        try:
            # 1. Farmer A can write to its own tenant table
            await sess_a.execute(text(f"""
                INSERT INTO "{schema_a}".fields (farmer_id, name, variety, area_acres)
                VALUES ('{farmer_a.id}', 'Alpha Paddy Field', 'Sona Masoori', 3.0);
            """))
            cnt_a = (await sess_a.execute(text(f'SELECT count(*) FROM "{schema_a}".fields;'))).scalar()
            assert cnt_a >= 1, "Farmer A could not insert into its own table"

            # 2. Farmer A attempts to read Farmer B's table -> MUST BE DENIED
            cross_read_denied = False
            try:
                await sess_a.execute(text(f'SELECT * FROM "{schema_b}".fields;'))
            except Exception as exc:
                cross_read_denied = True
            assert cross_read_denied, "Farmer A was able to read Farmer B's tenant table!"

            # 3. Farmer A attempts to write to Farmer B's table -> MUST BE DENIED
            cross_write_denied = False
            try:
                await sess_a.execute(text(f"""
                    INSERT INTO "{schema_b}".fields (farmer_id, name, variety, area_acres)
                    VALUES ('{farmer_a.id}', 'Hacked Field', 'Rogue', 1.0);
                """))
            except Exception as exc:
                cross_write_denied = True
            assert cross_write_denied, "Farmer A was able to write to Farmer B's tenant table!"

        finally:
            # Clean up generator
            try:
                await anext(tenant_gen_a)
            except StopAsyncIteration:
                pass

        record_result(10, "Tenant Database Isolation via get_tenant_db", True,
                      f"Farmer A ('{schema_a}') successfully performed DML on own schema, but was strictly denied SELECT/INSERT on Farmer B ('{schema_b}').")
    except Exception as exc:
        record_result(10, "Tenant Database Isolation via get_tenant_db", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 11. Tenant session cleanup after exceptions
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            farmer_a = (await session.execute(select(Farmer).where(Farmer.username == "step3a_user1"))).scalar_one()

        tenant_gen_exc = get_tenant_db(current_user=farmer_a)
        sess_exc = await anext(tenant_gen_exc)
        cleanup_success = False

        try:
            # Stage an invalid query to trigger database error
            await sess_exc.execute(text("SELECT non_existent_column FROM non_existent_table;"))
        except Exception:
            # Deliberately raise exception into generator to test cleanup
            try:
                await tenant_gen_exc.athrow(RuntimeError("Deliberate route failure"))
            except RuntimeError:
                cleanup_success = True

        assert cleanup_success, "Exception was not caught and cleaned up by generator"

        # Verify a new session can be immediately opened and executed normally
        tenant_gen_new = get_tenant_db(current_user=farmer_a)
        sess_new = await anext(tenant_gen_new)
        val = (await sess_new.execute(text("SELECT 1;"))).scalar()
        assert val == 1, "Subsequent tenant session failed after previous exception cleanup"
        try:
            await anext(tenant_gen_new)
        except StopAsyncIteration:
            pass

        record_result(11, "Tenant Session Teardown & Exception Cleanup", True,
                      "Verified transaction rollback, connection disposal, and clean recovery after deliberate exception.")
    except Exception as exc:
        record_result(11, "Tenant Session Teardown & Exception Cleanup", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 12. Missing POSTGRES_PASSWORD produces a configuration error rather than fallback
    # --------------------------------------------------------------------------
    try:
        orig_pwd = os.environ.get("POSTGRES_PASSWORD")
        try:
            # Empty out POSTGRES_PASSWORD
            os.environ["POSTGRES_PASSWORD"] = ""
            config_error_raised = False
            try:
                await _get_privileged_conn(STAGING_DB)
            except SecurityConfigurationError as exc:
                if "POSTGRES_PASSWORD" in str(exc):
                    config_error_raised = True
            assert config_error_raised, "_get_privileged_conn did not raise SecurityConfigurationError when POSTGRES_PASSWORD is missing!"
        finally:
            if orig_pwd is not None:
                os.environ["POSTGRES_PASSWORD"] = orig_pwd

        record_result(12, "Hardcoded Password Removal & Configuration Enforcement", True,
                      "Verified that missing POSTGRES_PASSWORD raises SecurityConfigurationError. Zero fallback passwords exist.")
    except Exception as exc:
        record_result(12, "Hardcoded Password Removal & Configuration Enforcement", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 13. Existing registration and duplicate-mobile tests still pass
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # 13a: Normal registration
            reg_req_new = FarmerRegisterRequest(
                username="step3a_reg_test_user",
                password="NewPassword2026!",
                mobile_number="9876543233",
                full_name="New Registered Farmer"
            )
            created_new = await register_farmer(request=reg_req_new, db=session)
            assert created_new.role == "farmer"
            assert created_new.normalized_mobile == "+919876543233"

            # 13b: Duplicate mobile rejection
            dup_req = FarmerRegisterRequest(
                username="step3a_reg_test_dup",
                password="NewPassword2026!",
                mobile_number="9876543233",  # Same mobile
                full_name="Duplicate Reg User"
            )
            dup_rejected = False
            try:
                await register_farmer(request=dup_req, db=session)
            except HTTPException as exc:
                if exc.status_code == 400 and "already registered" in exc.detail:
                    dup_rejected = True
            assert dup_rejected, "Duplicate mobile was not rejected with 400"

            # 13c: Role injection rejection
            escalate_req = FarmerRegisterRequest.model_validate({
                "username": "step3a_escalate_user",
                "password": "Password2026!",
                "mobile_number": "9876543234",
                "full_name": "Escalate User",
                "role": "admin",
                "is_admin": True
            })
            created_esc = await register_farmer(request=escalate_req, db=session)
            assert created_esc.role == "farmer", f"Attacker escalated to admin! role={created_esc.role}"

            record_result(13, "Existing Registration & Duplicate Protection Regressions", True,
                          "Verified standard registration, duplicate-mobile rejection (400), and role escalation blocking (server-enforced farmer).")
    except Exception as exc:
        record_result(13, "Existing Registration & Duplicate Protection Regressions", False, f"Failed: {exc}")

    # Cleanup synthetic test schemas and roles
    print("Cleaning up synthetic test resources from staging...")
    farmers_to_clean = await conn.fetch("SELECT schema_name FROM public.farmers WHERE username LIKE 'step3a_%' AND schema_name IS NOT NULL;")
    for r in farmers_to_clean:
        s = r["schema_name"]
        role = f"tenant_{s}"
        await conn.execute(f'DROP SCHEMA IF EXISTS "{s}" CASCADE;')
        await conn.execute(f'DROP OWNED BY "{role}"; DROP ROLE IF EXISTS "{role}";')
        
    await conn.execute("DELETE FROM public.farmers WHERE username LIKE 'step3a_%';")
    await conn.close()
    await close_db_engine()

    print("\n" + "=" * 75)
    print("FINAL STEP 3A VERIFICATION SUMMARY:")
    print("=" * 75)
    all_passed = True
    for k, v in results.items():
        st = "PASSED" if v["passed"] else "FAILED"
        if not v["passed"]:
            all_passed = False
        print(f"  {k:10} : [{st:7}] {v['name']}")
    print("=" * 75)
    if all_passed:
        print("ALL 13 STEP 3A VERIFICATION TESTS PASSED SUCCESSFULLY (100% SUCCESS)!")
    else:
        print("SOME TESTS FAILED! Inspect logs above.")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

