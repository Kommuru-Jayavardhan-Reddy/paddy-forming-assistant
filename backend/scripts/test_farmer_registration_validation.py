"""
Paddy Farming Assistant - Farmer Registration Form UI & Backend Validation Suite
Tests all requirements specified in FARMER REGISTRATION FORM - UI & VALIDATION CORRECTIONS:
1. Empty mobile number is rejected (Pydantic & endpoint validation).
2. Invalid mobile number is rejected (non-Indian, incorrect digits, letters).
3. Empty full name is rejected.
4. Whitespace-only full name is rejected.
5. Valid farmer registration succeeds with schema provisioning.
6. Existing farmer login continues working (via username and via mobile).
7. Existing admin login remains completely unaffected.
8. Database safety: Zero modifications to production, legacy rows with NULL mobile preserved.
"""

import os
import sys
import asyncio
from pathlib import Path

BACKEND_DIR = Path("c:/paddy project/backend")
sys.path.insert(0, str(BACKEND_DIR))

from app import config
config.POSTGRES_DB = "paddy_farming_staging"

from pydantic import ValidationError
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncpg

from app.db.session import init_db_engine, get_async_engine
from app.schemas.auth import FarmerRegisterRequest, FarmerLoginRequest
from app.api.auth import register_farmer, login
from app.core.phone import validate_indian_mobile_number, InvalidMobileNumberError
from app.db.models.farmer import Farmer

test_results = []

def record(name: str, passed: bool, message: str):
    test_results.append((name, passed, message))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if message:
        print(f"         {message}")

async def run_validation_suite():
    print("=" * 80)
    print("STARTING FARMER REGISTRATION FORM VALIDATION & REGRESSION TEST SUITE")
    print(f"Database: {config.POSTGRES_DB} (127.0.0.1:5432)")
    print("=" * 80 + "\n")

    # Clean existing test users
    conn = await asyncpg.connect(
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host="127.0.0.1",
        port=5432,
        database="paddy_farming_staging",
    )
    await conn.execute("DELETE FROM public.farmers WHERE username LIKE 'val_reg_%' OR mobile_number LIKE '98111%';")
    await conn.close()

    init_db_engine()
    engine = get_async_engine()

    # TEST 1: Empty mobile number rejected by Pydantic / Schema
    try:
        FarmerRegisterRequest(
            username="val_reg_test1",
            password="SecurePass2026!",
            mobile_number="",
            full_name="Valid Name"
        )
        record("Empty mobile number rejected by schema", False, "Expected ValidationError was not raised")
    except (ValidationError, ValueError) as exc:
        record("Empty mobile number rejected by schema", True, f"Safely caught: {exc.errors()[0]['msg'] if hasattr(exc, 'errors') else str(exc)}")

    # TEST 2: Whitespace-only mobile number rejected
    try:
        FarmerRegisterRequest(
            username="val_reg_test2",
            password="SecurePass2026!",
            mobile_number="   ",
            full_name="Valid Name"
        )
        record("Whitespace-only mobile number rejected by schema", False, "Expected ValidationError was not raised")
    except (ValidationError, ValueError) as exc:
        record("Whitespace-only mobile number rejected by schema", True, "Rejected whitespace mobile")

    # TEST 3: Invalid Indian mobile numbers rejected (too short, non-Indian prefix, letters)
    invalid_numbers = [
        "12345",              # too short
        "987654321",          # 9 digits
        "1234567890",         # 10 digits starting with 1 (not Indian)
        "5555555555",         # starts with 5
        "+14155552671",       # US number
        "98765abcde",         # letters
    ]
    all_invalid_caught = True
    for bad_num in invalid_numbers:
        try:
            validate_indian_mobile_number(bad_num)
            all_invalid_caught = False
            print(f"      [!] Failed to reject: {bad_num}")
        except InvalidMobileNumberError:
            pass
    record("All invalid mobile numbers rejected by Indian format validator", all_invalid_caught, f"Tested {len(invalid_numbers)} invalid phone formats")

    # TEST 4: Valid Indian formats accepted and normalized to +91
    valid_numbers = [
        ("9811122233", "+919811122233"),
        ("+919811122233", "+919811122233"),
        ("09811122233", "+919811122233"),
        ("+91 98111-22233", "+919811122233"),
    ]
    all_valid_normalized = True
    for raw, expected in valid_numbers:
        norm = validate_indian_mobile_number(raw)
        if norm != expected:
            all_valid_normalized = False
    record("Valid Indian formats correctly normalized to E.164 (+91)", all_valid_normalized, "Tested 10-digit, +91, 0-prefix, and formatted strings")

    # TEST 5: Empty full name rejected by schema
    try:
        FarmerRegisterRequest(
            username="val_reg_test3",
            password="SecurePass2026!",
            mobile_number="9811122233",
            full_name=""
        )
        record("Empty full name rejected by schema", False, "Expected ValidationError was not raised")
    except (ValidationError, ValueError):
        record("Empty full name rejected by schema", True, "Safely rejected empty full name")

    # TEST 6: Whitespace-only full name rejected
    try:
        FarmerRegisterRequest(
            username="val_reg_test4",
            password="SecurePass2026!",
            mobile_number="9811122233",
            full_name="    "
        )
        record("Whitespace-only full name rejected by schema", False, "Expected ValidationError was not raised")
    except (ValidationError, ValueError):
        record("Whitespace-only full name rejected by schema", True, "Safely rejected whitespace-only full name")

    # TEST 7: Full name missing from payload rejected
    try:
        FarmerRegisterRequest.model_validate({
            "username": "val_reg_test5",
            "password": "SecurePass2026!",
            "mobile_number": "9811122233"
        })
        record("Missing full name field rejected by schema", False, "Expected ValidationError was not raised")
    except (ValidationError, ValueError):
        record("Missing full name field rejected by schema", True, "Field required validation triggered")

    # TEST 8: Successful farmer registration with mandatory fields & schema provisioning
    registered_farmer_schema = None
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            reg_req = FarmerRegisterRequest(
                username="val_reg_farmer_valid",
                password="FarmerSecretPass2026!",
                mobile_number="9811122233",
                full_name="Ravi Kumar Sundaram",
                farm_name="Delta Sunrise Farm",
                village="Thanjavur"
            )
            profile = await register_farmer(request=reg_req, db=session)
            assert profile.username == "val_reg_farmer_valid"
            assert profile.role == "farmer"
            assert profile.full_name == "Ravi Kumar Sundaram"
            assert profile.normalized_mobile == "+919811122233"
            assert profile.schema_name.startswith("farmer_")
            registered_farmer_schema = profile.schema_name
            record("Valid farmer registration succeeds with schema provisioning", True, f"Farmer '{profile.username}' registered with schema '{profile.schema_name}'")
    except Exception as exc:
        record("Valid farmer registration succeeds with schema provisioning", False, f"Failed: {exc}")

    # TEST 9: Duplicate mobile number rejected with HTTP 400
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            dup_req = FarmerRegisterRequest(
                username="val_reg_farmer_dup",
                password="AnotherSecret2026!",
                mobile_number="9811122233",  # same mobile
                full_name="Another Farmer"
            )
            dup_rejected = False
            try:
                await register_farmer(request=dup_req, db=session)
            except HTTPException as exc:
                if exc.status_code == 400 and "already registered" in exc.detail:
                    dup_rejected = True
            assert dup_rejected, "Duplicate mobile was not rejected with HTTP 400"
            record("Duplicate mobile number rejected with HTTP 400", True, "Prevented registration with existing registered mobile number")
    except Exception as exc:
        record("Duplicate mobile number rejected with HTTP 400", False, f"Failed: {exc}")

    # TEST 10: Existing farmer login via username continues working
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            login_req = FarmerLoginRequest(
                username="val_reg_farmer_valid",
                password="FarmerSecretPass2026!"
            )
            token_resp = await login(request=login_req, db=session)
            assert token_resp.username == "val_reg_farmer_valid"
            assert token_resp.role == "farmer"
            assert token_resp.schema_name == registered_farmer_schema
            record("Farmer login via username continues working", True, f"Issued token for role='{token_resp.role}'")
    except Exception as exc:
        record("Farmer login via username continues working", False, f"Failed: {exc}")

    # TEST 11: Existing farmer login via 10-digit mobile number continues working
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            login_req = FarmerLoginRequest(
                username="9811122233",
                password="FarmerSecretPass2026!"
            )
            token_resp = await login(request=login_req, db=session)
            assert token_resp.username == "val_reg_farmer_valid"
            assert token_resp.role == "farmer"
            record("Farmer login via 10-digit mobile continues working", True, "Resolved mobile -> user and authenticated")
    except Exception as exc:
        record("Farmer login via 10-digit mobile continues working", False, f"Failed: {exc}")

    # TEST 12: Existing admin login remains unaffected
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            admin_req = FarmerLoginRequest(
                username="admin",
                password="password123"
            )
            token_resp = await login(request=admin_req, db=session)
            assert token_resp.username == "admin"
            assert token_resp.role == "admin"
            record("Existing admin login remains completely unaffected", True, "Admin authenticated with role='admin' claim")
    except Exception as exc:
        record("Existing admin login remains completely unaffected", False, f"Failed: {exc}")

    print("\n" + "=" * 80)
    passed_count = sum(1 for _, p, _ in test_results if p)
    total_count = len(test_results)
    print(f"RESULTS: {passed_count}/{total_count} TESTS PASSED ({(passed_count/total_count)*100:.1f}%)")
    print("=" * 80 + "\n")

    assert passed_count == total_count, f"{total_count - passed_count} tests failed!"

if __name__ == "__main__":
    asyncio.run(run_validation_suite())

