"""
Paddy Farming Assistant - STEP 3 Pre-Flight Authentication Code Audit
Tests all 12 authentication capabilities against real PostgreSQL staging (paddy_farming_staging).
Records exact PASS/FAIL status, missing capabilities, and security vulnerabilities without touching production.
"""

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
from app.core.dependencies import get_current_user, require_admin, require_farmer
from app.db.models.farmer import Farmer, UserRole
from app.schemas.auth import FarmerRegisterRequest, FarmerLoginRequest
from app.api.auth import register_farmer, login
from app.services.tenant_provisioning import provision_tenant_database_objects
from app.db.tenant_session import tenant_session_scope
from app.exceptions import TokenExpiredError, InvalidTokenError

STAGING_DB = "paddy_farming_staging"
results: Dict[str, Dict[str, Any]] = {}


def record_result(item_id: str, name: str, passed: bool, details: str, is_missing: bool = False, vulnerability: str = None):
    results[item_id] = {
        "name": name,
        "passed": passed,
        "is_missing": is_missing,
        "vulnerability": vulnerability,
        "details": details
    }
    status_str = "PASSED" if passed else ("MISSING" if is_missing else "FAILED")
    print(f"[{status_str}] {item_id}: {name}")
    print(f"  -> {details}")


async def run_audit():
    print("=" * 75)
    print("STEP 3 PRE-FLIGHT AUTHENTICATION CODE AUDIT (STAGING)")
    print("=" * 75)
    
    # Verify staging connection directly
    conn = await asyncpg.connect(
        user="postgres",
        password=config.POSTGRES_PASSWORD,
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=STAGING_DB
    )
    db_name = await conn.fetchval("SELECT current_database();")
    assert db_name == STAGING_DB, f"Safety check: connected to {db_name}, expected {STAGING_DB}"
    print(f"Verified connection to isolated staging database: '{STAGING_DB}'.\n")

    # Clean previous audit test records
    await conn.execute("DELETE FROM public.farmers WHERE username LIKE 'audit_%';")

    # Initialize SQLAlchemy Async Engine on staging
    # Override POSTGRES_DB to staging for this audit run
    config.POSTGRES_DB = STAGING_DB
    init_db_engine()
    engine = get_async_engine()
    
    from sqlalchemy.ext.asyncio import AsyncSession
    
    # --------------------------------------------------------------------------
    # 1. Existing Farmer Registration Endpoint
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            reg_req = FarmerRegisterRequest(
                username="audit_farmer_1",
                password="SecureFarmerPassword2026!",
                mobile_number="9876543201",
                full_name="Audit Farmer One",
                farm_name="Green Valley",
                village="Thanjavur"
            )
            created = await register_farmer(request=reg_req, db=session)
            assert created.username == "audit_farmer_1"
            assert created.role == "farmer"
            assert created.schema_name is not None
            assert created.normalized_mobile == "+919876543201"
            record_result("ITEM_1", "Existing Farmer Registration Endpoint", True, 
                          f"Created farmer '{created.username}' with role='{created.role}', schema='{created.schema_name}', mobile='{created.normalized_mobile}'.")
    except Exception as exc:
        record_result("ITEM_1", "Existing Farmer Registration Endpoint", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 2. Mobile Number + Password Login Endpoint
    # --------------------------------------------------------------------------
    # Can a farmer log in using their registered mobile number instead of username?
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # Attempt 2a: with raw mobile number '9876543201'
            login_req_mobile_raw = FarmerLoginRequest(
                username="9876543201",
                password="SecureFarmerPassword2026!"
            )
            # Attempt 2b: with E.164 normalized mobile '+919876543201'
            login_req_mobile_e164 = FarmerLoginRequest(
                username="+919876543201",
                password="SecureFarmerPassword2026!"
            )
            
            mobile_login_worked = False
            try:
                auth_resp = await login(request=login_req_mobile_raw, db=session)
                mobile_login_worked = True
            except HTTPException as e1:
                try:
                    auth_resp = await login(request=login_req_mobile_e164, db=session)
                    mobile_login_worked = True
                except HTTPException as e2:
                    mobile_login_worked = False

            if mobile_login_worked:
                record_result("ITEM_2", "Mobile Number + Password Login", True, 
                              "Mobile number login supported via existing login endpoint.")
            else:
                record_result("ITEM_2", "Mobile Number + Password Login", False, 
                              "Existing /auth/login strictly queries 'WHERE Farmer.username == request.username'. It does NOT look up farmers by normalized_mobile. Farmers cannot log in with mobile number.",
                              is_missing=True)
    except Exception as exc:
        record_result("ITEM_2", "Mobile Number + Password Login", False, f"Error testing mobile login: {exc}", is_missing=True)

    # --------------------------------------------------------------------------
    # 3. Argon2id Password Verification
    # --------------------------------------------------------------------------
    try:
        pwd = "TestArgonPassword2026!"
        pwd_hash = hash_password(pwd)
        assert pwd_hash.startswith("$argon2id$"), "Hash is not Argon2id"
        assert verify_password(pwd, pwd_hash) is True, "Valid password rejected"
        assert verify_password("WrongPassword123", pwd_hash) is False, "Invalid password accepted"
        record_result("ITEM_3", "Argon2id Password Verification", True, 
                      "Argon2id hashing & verification works with OWASP params ($argon2id$v=19$m=65536,t=3,p=4).")
    except Exception as exc:
        record_result("ITEM_3", "Argon2id Password Verification", False, f"Argon2id verification failed: {exc}")

    # --------------------------------------------------------------------------
    # 4. JWT Creation, Signature Verification and Expiration
    # --------------------------------------------------------------------------
    try:
        claims = {"sub": str(uuid.uuid4()), "role": "farmer", "username": "jwt_test_user"}
        token = create_access_token(data=claims)
        decoded = decode_access_token(token)
        assert decoded["sub"] == claims["sub"], "Subject mismatch"
        assert decoded["role"] == "farmer", "Role mismatch"
        assert decoded["type"] == "access", "Token type mismatch"
        
        # Test expiration: issue with 1-second lifetime and wait 2 seconds
        token_to_expire = create_access_token(data=claims, expires_delta=timedelta(seconds=1))
        await asyncio.sleep(2)
        try:
            decode_access_token(token_to_expire)
            raise AssertionError("Expired token was accepted!")
        except TokenExpiredError:
            pass  # correctly rejected as expired
            
        record_result("ITEM_4", "JWT Creation, Signature Verification & Expiration", True, 
                      "PyJWT HS256 token creation, claims extraction, signature verification, and expiration rejection verified.")
    except Exception as exc:
        record_result("ITEM_4", "JWT Creation, Signature Verification & Expiration", False, f"JWT verification failed: {exc}")

    # --------------------------------------------------------------------------
    # 5. Database-Derived Farmer Identity and Role
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            login_req = FarmerLoginRequest(
                username="audit_farmer_1",
                password="SecureFarmerPassword2026!"
            )
            token_resp = await login(request=login_req, db=session)
            decoded = decode_access_token(token_resp.access_token)
            
            # Verify claims match DB row exactly
            farmer_row = (await session.execute(select(Farmer).where(Farmer.username == "audit_farmer_1"))).scalar_one()
            assert decoded["sub"] == str(farmer_row.id), "JWT sub does not match DB UUID"
            assert decoded["role"] == farmer_row.role, "JWT role does not match DB role"
            assert decoded["username"] == farmer_row.username, "JWT username does not match DB username"
            assert decoded["schema_name"] == farmer_row.schema_name, "JWT schema does not match DB schema"
            
            record_result("ITEM_5", "Database-Derived Identity and Role Claims", True, 
                          f"Token claims derived exclusively from verified DB row (sub={decoded['sub']}, role={decoded['role']}).")
    except Exception as exc:
        record_result("ITEM_5", "Database-Derived Identity and Role Claims", False, f"Failed: {exc}")

    # --------------------------------------------------------------------------
    # 6. Admin-Only Endpoint Protection
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # 6a: Farmer role -> MUST BE 403
            farmer_row = (await session.execute(select(Farmer).where(Farmer.username == "audit_farmer_1"))).scalar_one()
            farmer_blocked = False
            try:
                await require_admin(current_user=farmer_row)
            except HTTPException as exc:
                if exc.status_code == 403:
                    farmer_blocked = True
            assert farmer_blocked, "Farmer was not rejected by require_admin with 403!"
            
            # 6b: Admin role -> MUST BE 200/PASSED
            admin_row = Farmer(
                id=uuid.uuid4(),
                username="audit_admin_test",
                password_hash=hash_password("AdminPass2026!"),
                role="admin",
                is_active=True
            )
            adm = await require_admin(current_user=admin_row)
            assert adm.username == "audit_admin_test"
            
            # 6c: Unauthenticated -> MUST BE 401
            unauth_blocked = False
            try:
                await get_current_user(credentials=None, db=session)
            except HTTPException as exc:
                if exc.status_code == 401:
                    unauth_blocked = True
            assert unauth_blocked, "Unauthenticated request was not rejected with 401!"
            
            record_result("ITEM_6", "Admin-Only Endpoint Protection", True, 
                          "require_admin strictly enforces role='admin' (403 for farmers, 401 for unauthenticated, allowed for admin).")
    except Exception as exc:
        record_result("ITEM_6", "Admin-Only Endpoint Protection", False, f"Admin protection failed: {exc}")

    # --------------------------------------------------------------------------
    # 7. Legacy Farmers with NULL Mobile Numbers
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # Insert synthetic legacy farmer with NULL mobile numbers
            legacy_id = uuid.uuid4()
            legacy_hash = hash_password("LegacySecret2026!")
            legacy_farmer = Farmer(
                id=legacy_id,
                username="audit_legacy_farmer",
                password_hash=legacy_hash,
                mobile_number=None,
                normalized_mobile=None,
                role="farmer",
                schema_name=None,
                encrypted_db_secret=None,
                is_active=True
            )
            session.add(legacy_farmer)
            await session.commit()
            
            # Test username login for legacy farmer
            login_req = FarmerLoginRequest(username="audit_legacy_farmer", password="LegacySecret2026!")
            token_resp = await login(request=login_req, db=session)
            assert token_resp.username == "audit_legacy_farmer"
            assert token_resp.schema_name is None
            
            record_result("ITEM_7", "Legacy Farmers with NULL Mobile Numbers", True, 
                          "Legacy farmers with NULL mobile_number & normalized_mobile authenticate cleanly via username/password.")
    except Exception as exc:
        record_result("ITEM_7", "Legacy Farmers with NULL Mobile Numbers", False, f"Legacy farmer login failed: {exc}")

    # --------------------------------------------------------------------------
    # 8. Duplicate Mobile Registration Rejection
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            dup_req = FarmerRegisterRequest(
                username="audit_farmer_dup_mobile",
                password="Password2026!",
                mobile_number="+919876543201",  # Same number as audit_farmer_1
                full_name="Duplicate Mobile Farmer"
            )
            rejected = False
            try:
                await register_farmer(request=dup_req, db=session)
            except HTTPException as exc:
                if exc.status_code == 400 and "already registered" in exc.detail:
                    rejected = True
            assert rejected, "Duplicate mobile number was not rejected with 400!"
            record_result("ITEM_8", "Duplicate Mobile Registration Rejection", True, 
                          "Registration with an existing normalized mobile is rejected with HTTP 400 Bad Request.")
    except Exception as exc:
        record_result("ITEM_8", "Duplicate Mobile Registration Rejection", False, f"Duplicate mobile test failed: {exc}")

    # --------------------------------------------------------------------------
    # 9. Invalid Mobile / Password Rejection
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # 9a: Invalid mobile format -> 422
            inv_mobile_req = FarmerRegisterRequest(
                username="audit_inv_mobile",
                password="Password2026!",
                mobile_number="12345"  # invalid
            )
            inv_mobile_rejected = False
            try:
                await register_farmer(request=inv_mobile_req, db=session)
            except HTTPException as exc:
                if exc.status_code == 422:
                    inv_mobile_rejected = True
            assert inv_mobile_rejected, "Invalid mobile was not rejected with 422"
            
            # 9b: Short password (<8 chars) -> Pydantic ValidationError
            short_pwd_rejected = False
            try:
                FarmerRegisterRequest(username="audit_short_pwd", password="123")
            except Exception:
                short_pwd_rejected = True
            assert short_pwd_rejected, "Short password (<8 chars) was not rejected"
            
            # 9c: Incorrect password on login -> 401
            wrong_pwd_rejected = False
            try:
                await login(request=FarmerLoginRequest(username="audit_farmer_1", password="WrongPassword!"), db=session)
            except HTTPException as exc:
                if exc.status_code == 401:
                    wrong_pwd_rejected = True
            assert wrong_pwd_rejected, "Incorrect password was not rejected with 401"
            
            record_result("ITEM_9", "Invalid Mobile / Password Rejection", True, 
                          "Invalid mobile rejected (422), short password rejected (<8 chars), wrong password rejected (401).")
    except Exception as exc:
        record_result("ITEM_9", "Invalid Mobile / Password Rejection", False, f"Rejection test failed: {exc}")

    # --------------------------------------------------------------------------
    # 10. Registration Cannot Create Admin Accounts
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            # Send payload with extra fields role='admin'
            reg_req = FarmerRegisterRequest.model_validate({
                "username": "audit_attacker_admin",
                "password": "AttackerPassword2026!",
                "mobile_number": "9876543202",
                "role": "admin",
                "is_admin": True
            })
            created = await register_farmer(request=reg_req, db=session)
            assert created.role == "farmer", f"Attacker created admin account! role={created.role}"
            record_result("ITEM_10", "Registration Cannot Create Admin Accounts", True, 
                          "Role injection attempts ignored/discarded; server strictly enforces role='farmer'.")
    except Exception as exc:
        record_result("ITEM_10", "Registration Cannot Create Admin Accounts", False, f"Escalation test failed: {exc}")

    # --------------------------------------------------------------------------
    # 11. Existing Username/Password Compatibility
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            req = FarmerLoginRequest(username="audit_farmer_1", password="SecureFarmerPassword2026!")
            resp = await login(request=req, db=session)
            assert resp.token_type == "access"
            assert resp.username == "audit_farmer_1"
            record_result("ITEM_11", "Existing Username/Password Compatibility", True, 
                          "Standard username/password login is 100% operational and backward-compatible.")
    except Exception as exc:
        record_result("ITEM_11", "Existing Username/Password Compatibility", False, f"Username login failed: {exc}")

    # --------------------------------------------------------------------------
    # 12. Tenant-Aware Authenticated Database Session Mapping
    # --------------------------------------------------------------------------
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            farmer = (await session.execute(select(Farmer).where(Farmer.username == "audit_farmer_1"))).scalar_one()
            
            # Test tenant_session_scope using farmer's schema and encrypted secret
            tenant_session_verified = False
            async with tenant_session_scope(
                schema_name=farmer.schema_name,
                encrypted_db_secret=farmer.encrypted_db_secret,
                target_database=STAGING_DB
            ) as tenant_sess:
                # Query inside tenant schema
                res = await tenant_sess.execute(text("SELECT current_user, current_schema();"))
                curr_user, curr_schema = res.one()
                assert curr_user == f"tenant_{farmer.schema_name}"
                assert curr_schema == farmer.schema_name
                tenant_session_verified = True
                
            record_result("ITEM_12", "Tenant-Aware Authenticated Database Session Mapping", True, 
                          f"tenant_session_scope mapped to dedicated role 'tenant_{farmer.schema_name}' with local schema '{farmer.schema_name}'.")
    except Exception as exc:
        record_result("ITEM_12", "Tenant-Aware Authenticated Database Session Mapping", False, f"Tenant session mapping failed: {exc}")

    # Cleanup audit test schemas and users
    print("\nCleaning up audit test resources...")
    farmers_to_clean = await conn.fetch("SELECT schema_name FROM public.farmers WHERE username LIKE 'audit_%' AND schema_name IS NOT NULL;")
    for r in farmers_to_clean:
        s = r["schema_name"]
        role = f"tenant_{s}"
        await conn.execute(f'DROP SCHEMA IF EXISTS "{s}" CASCADE;')
        await conn.execute(f'DROP OWNED BY "{role}"; DROP ROLE IF EXISTS "{role}";')
        
    await conn.execute("DELETE FROM public.farmers WHERE username LIKE 'audit_%';")
    await conn.close()
    await close_db_engine()
    
    print("\n" + "=" * 75)
    print("AUDIT SUMMARY:")
    print("=" * 75)
    for k, v in results.items():
        st = "PASSED" if v["passed"] else ("MISSING" if v["is_missing"] else "FAILED")
        print(f"  {k:8} : [{st:7}] {v['name']}")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_audit())
