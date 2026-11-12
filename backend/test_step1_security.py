"""
Paddy Farming Assistant - Step 1 Final JWT Test Verification Suite
Validates:
1. Argon2id password hashing and verification (Preserved).
2. create_access_token() strictly enforces token_type="access" and rejects arbitrary types.
3. Explicit strict rejection of boolean values for exp, iat, and nbf claims with exact rejection reasons.
4. Independent testing of nbf > exp semantic check where both timestamps are in the past.
5. PyJWT & temporal nbf (future nbf) and missing nbf validation.
6. Strict HS256 algorithm enforcement.
7. Token expiration, tampering, and foreign secret signature rejection.
8. Security configuration guard without leaking secret values.
"""

import sys
import uuid
from datetime import timedelta, datetime, timezone
from pathlib import Path

# Ensure backend directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import jwt
from app import config
from app.core.security import (
    hash_password,
    verify_password,
    needs_rehash,
    create_access_token,
    decode_access_token,
    APPROVED_JWT_ALGORITHM,
    TOKEN_TYPE_ACCESS,
)
from app.exceptions import (
    TokenExpiredError,
    InvalidTokenError,
    SecurityConfigurationError,
)


def test_argon2id_hashing_and_verification():
    print("\n--- [1] Testing Argon2id Password Hashing & Verification (Preserved) ---")
    test_password = "PaddyFarmer@StrongPass2026!"
    
    hashed = hash_password(test_password)
    assert hashed.startswith("$argon2id$"), f"Expected $argon2id$ hash prefix, got {hashed[:15]}"
    assert "$m=65536,t=3,p=4$" in hashed, f"Expected OWASP parameters, got {hashed}"
    print("  [PASS] Hash format and parameters match Argon2id RFC 9106 specs.")
    
    assert verify_password(test_password, hashed) is True
    print("  [PASS] Correct password verified successfully.")
    
    assert verify_password("WrongPassword123", hashed) is False
    print("  [PASS] Incorrect password rejected as False.")
    
    assert verify_password("", hashed) is False
    assert verify_password(test_password, "") is False
    assert verify_password(test_password, "invalid_hash_format") is False
    assert verify_password(None, hashed) is False
    print("  [PASS] Malformed/empty inputs safely returned False without uncaught exceptions.")
    
    assert needs_rehash(hashed) is False
    print("  [PASS] needs_rehash returned False for freshly generated Argon2id hash.")


def test_enforce_token_type_access_only():
    print("\n--- [2] Testing Enforcement of token_type='access' in create_access_token() ---")
    user_id = str(uuid.uuid4())
    
    # 1. Normal access token creation
    token = create_access_token({"sub": user_id})
    payload = decode_access_token(token)
    assert payload["type"] == TOKEN_TYPE_ACCESS, f"Expected 'access', got {payload['type']}"
    print(f"  [PASS] Normal token created with verified type='{TOKEN_TYPE_ACCESS}'.")
    
    # 2. Rejection of conflicting type 'refresh'
    try:
        create_access_token({"sub": user_id, "type": "refresh"})
        assert False, "Should reject arbitrary token type 'refresh'!"
    except ValueError as exc:
        expected_msg = "create_access_token() strictly creates 'access' tokens. Conflicting type 'refresh' is forbidden."
        assert str(exc) == expected_msg, f"Expected '{expected_msg}', got '{exc}'"
        print(f"  [PASS] Conflicting type 'refresh' rejected with exact error: {exc}")

    # 3. Rejection of conflicting type 'id_token'
    try:
        create_access_token({"sub": user_id, "type": "id_token"})
        assert False, "Should reject arbitrary token type 'id_token'!"
    except ValueError as exc:
        expected_msg = "create_access_token() strictly creates 'access' tokens. Conflicting type 'id_token' is forbidden."
        assert str(exc) == expected_msg, f"Expected '{expected_msg}', got '{exc}'"
        print(f"  [PASS] Conflicting type 'id_token' rejected with exact error: {exc}")


def test_reject_boolean_claims_explicit_type_check():
    print("\n--- [3] Testing Explicit Strict Rejection of Boolean Claims (exp, iat, nbf) ---")
    secret = config.JWT_SECRET_KEY
    now = datetime.now(timezone.utc)
    valid_ts = int(now.timestamp())
    exp_ts = valid_ts + 3600
    
    # 1. Reject exp=True (demonstrating rejection via explicit type validation, not expiration)
    token_exp_true = jwt.encode(
        {"sub": "user-1", "type": "access", "exp": True, "iat": valid_ts, "nbf": valid_ts},
        secret,
        algorithm="HS256",
    )
    try:
        decode_access_token(token_exp_true)
        assert False, "Should reject token with exp=True!"
    except InvalidTokenError as exc:
        expected = "Token 'exp' claim must be a numeric timestamp (excluding boolean)."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] exp=True rejected by explicit strict type validation: '{exc.message}'")

    # 2. Reject exp=False
    token_exp_false = jwt.encode(
        {"sub": "user-1", "type": "access", "exp": False, "iat": valid_ts, "nbf": valid_ts},
        secret,
        algorithm="HS256",
    )
    try:
        decode_access_token(token_exp_false)
        assert False, "Should reject token with exp=False!"
    except InvalidTokenError as exc:
        expected = "Token 'exp' claim must be a numeric timestamp (excluding boolean)."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] exp=False rejected by explicit strict type validation: '{exc.message}'")

    # 3. Reject iat=True
    token_iat_true = jwt.encode(
        {"sub": "user-1", "type": "access", "exp": exp_ts, "iat": True, "nbf": valid_ts},
        secret,
        algorithm="HS256",
    )
    try:
        decode_access_token(token_iat_true)
        assert False, "Should reject token with iat=True!"
    except InvalidTokenError as exc:
        expected = "Token 'iat' claim must be a numeric timestamp (excluding boolean)."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] iat=True rejected by explicit strict type validation: '{exc.message}'")

    # 4. Reject iat=False
    token_iat_false = jwt.encode(
        {"sub": "user-1", "type": "access", "exp": exp_ts, "iat": False, "nbf": valid_ts},
        secret,
        algorithm="HS256",
    )
    try:
        decode_access_token(token_iat_false)
        assert False, "Should reject token with iat=False!"
    except InvalidTokenError as exc:
        expected = "Token 'iat' claim must be a numeric timestamp (excluding boolean)."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] iat=False rejected by explicit strict type validation: '{exc.message}'")

    # 5. Reject nbf=True
    token_nbf_true = jwt.encode(
        {"sub": "user-1", "type": "access", "exp": exp_ts, "iat": valid_ts, "nbf": True},
        secret,
        algorithm="HS256",
    )
    try:
        decode_access_token(token_nbf_true)
        assert False, "Should reject token with nbf=True!"
    except InvalidTokenError as exc:
        expected = "Token 'nbf' claim must be a numeric timestamp (excluding boolean)."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] nbf=True rejected by explicit strict type validation: '{exc.message}'")

    # 6. Reject nbf=False
    token_nbf_false = jwt.encode(
        {"sub": "user-1", "type": "access", "exp": exp_ts, "iat": valid_ts, "nbf": False},
        secret,
        algorithm="HS256",
    )
    try:
        decode_access_token(token_nbf_false)
        assert False, "Should reject token with nbf=False!"
    except InvalidTokenError as exc:
        expected = "Token 'nbf' claim must be a numeric timestamp (excluding boolean)."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] nbf=False rejected by explicit strict type validation: '{exc.message}'")


def test_nbf_greater_than_exp_both_in_past():
    print("\n--- [4] Testing Independent nbf > exp Semantic Validation (Both Timestamps in Past) ---")
    secret = config.JWT_SECRET_KEY
    now_ts = datetime.now(timezone.utc).timestamp()
    
    # Both nbf and exp are in the past, but nbf is chronologically later than exp:
    # iat = 2 hours ago
    # exp = 40 minutes ago (in the past!)
    # nbf = 20 minutes ago (in the past, but nbf > exp!)
    past_iat = int(now_ts - 7200)
    past_exp = int(now_ts - 2400)
    past_nbf = int(now_ts - 1200)
    
    assert past_nbf < now_ts, "nbf must be in the past for this test"
    assert past_exp < now_ts, "exp must be in the past for this test"
    assert past_nbf > past_exp, "nbf must be strictly greater than exp"
    
    token = jwt.encode(
        {"sub": "user-past", "type": "access", "exp": past_exp, "iat": past_iat, "nbf": past_nbf},
        secret,
        algorithm="HS256",
    )
    
    try:
        decode_access_token(token)
        assert False, "Should reject token where nbf > exp even when both are in the past!"
    except InvalidTokenError as exc:
        # Crucial: Must be rejected by the explicit semantic check, NOT as TokenExpiredError!
        expected = "Token 'nbf' claim cannot be later than 'exp' claim."
        assert exc.message == expected, f"Expected '{expected}', but got '{exc.message}'"
        print(f"  [PASS] Token with both timestamps in past rejected specifically by semantic check: '{exc.message}'")


def test_nbf_future_immature_and_missing():
    print("\n--- [5] Testing Future nbf (Immature) & Missing nbf Rejections ---")
    secret = config.JWT_SECRET_KEY
    now_ts = int(datetime.now(timezone.utc).timestamp())
    
    # 1. Future nbf (10 minutes in future)
    future_nbf = now_ts + 600
    token_future_nbf = jwt.encode(
        {"sub": "user-future", "type": "access", "exp": now_ts + 3600, "iat": now_ts, "nbf": future_nbf},
        secret,
        algorithm="HS256",
    )
    try:
        decode_access_token(token_future_nbf)
        assert False, "Should reject token with future nbf!"
    except InvalidTokenError as exc:
        expected = "Authentication token is not yet valid (nbf in future)."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] Future nbf rejected with exact message: '{exc.message}'")

    # 2. Missing nbf claim
    token_no_nbf = jwt.encode(
        {"sub": "user-no-nbf", "type": "access", "exp": now_ts + 3600, "iat": now_ts},
        secret,
        algorithm="HS256",
    )
    try:
        decode_access_token(token_no_nbf)
        assert False, "Should reject token missing nbf!"
    except InvalidTokenError as exc:
        assert "missing mandatory token claim" in exc.message.lower() and "nbf" in exc.message.lower()
        print(f"  [PASS] Missing mandatory nbf claim rejected with exact message: '{exc.message}'")


def test_jwt_mandatory_claims_validation():
    print("\n--- [6] Testing Mandatory Claims ('sub', 'exp', 'iat', 'nbf', 'type') ---")
    user_id = str(uuid.uuid4())
    claims = {
        "sub": user_id,
        "username": "kavitha_farmer",
        "role": "farmer",
        "mobile_number": "9876543210",
    }
    
    token = create_access_token(claims)
    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["type"] == TOKEN_TYPE_ACCESS
    assert isinstance(payload["exp"], (int, float)) and not isinstance(payload["exp"], bool)
    assert isinstance(payload["iat"], (int, float)) and not isinstance(payload["iat"], bool)
    assert isinstance(payload["nbf"], (int, float)) and not isinstance(payload["nbf"], bool)
    print("  [PASS] All 5 mandatory claims verified as genuine numeric timestamps and strings.")


def test_jwt_strict_algorithm_enforcement():
    print("\n--- [7] Testing Strict HS256 Algorithm Enforcement ---")
    assert APPROVED_JWT_ALGORITHM == "HS256"
    assert config.JWT_ALGORITHM == "HS256"
    assert config.ALLOWED_JWT_ALGORITHMS == ["HS256"]
    
    # Reject 'none' algorithm
    token_none = jwt.encode(
        {"sub": "attacker", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(hours=1), "iat": datetime.now(timezone.utc), "nbf": datetime.now(timezone.utc)},
        key=None,
        algorithm=None,
    )
    try:
        decode_access_token(token_none)
        assert False, "Should reject token signed with 'none' algorithm!"
    except InvalidTokenError as exc:
        expected = "Token signed with an unapproved algorithm."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] 'none' algorithm rejected with exact message: '{exc.message}'")


def test_jwt_expired_token_handling():
    print("\n--- [8] Testing Expired Token Rejection (where nbf <= exp) ---")
    secret = config.JWT_SECRET_KEY
    now_ts = int(datetime.now(timezone.utc).timestamp())
    # Issued 2 hours ago, valid from 2 hours ago, expired 1 hour ago (nbf <= exp < now):
    past_iat = now_ts - 7200
    past_nbf = now_ts - 7200
    past_exp = now_ts - 3600
    
    expired_token = jwt.encode(
        {"sub": "expired-user", "type": "access", "exp": past_exp, "iat": past_iat, "nbf": past_nbf},
        secret,
        algorithm="HS256",
    )
    
    try:
        decode_access_token(expired_token)
        assert False, "Expired token should raise TokenExpiredError!"
    except TokenExpiredError as exc:
        assert exc.status_code == 401
        expected = "Authentication token has expired. Please log in again."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] Expired token correctly raised TokenExpiredError with exact message: '{exc.message}'")



def test_jwt_tampered_and_malformed_tokens():
    print("\n--- [9] Testing Tampered, Malformed, and Empty Tokens ---")
    valid_token = create_access_token({"sub": "legit-user"})
    
    # 1. Tampered payload
    parts = valid_token.split(".")
    tampered_token = f"{parts[0]}.eyJuZXdfcGF5bG9hZCI6ICJoYWNrZWQifQ.{parts[2]}"
    try:
        decode_access_token(tampered_token)
        assert False, "Tampered token should raise InvalidTokenError!"
    except InvalidTokenError as exc:
        expected = "Token signature verification failed."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] Tampered token rejected with exact message: '{exc.message}'")
        
    # 2. Malformed string
    try:
        decode_access_token("this.is.not.a.valid.jwt")
        assert False, "Malformed token should raise InvalidTokenError!"
    except InvalidTokenError as exc:
        expected = "Malformed or undecodable authentication token."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] Malformed token rejected with exact message: '{exc.message}'")
        
    # 3. Empty token
    try:
        decode_access_token("")
        assert False, "Empty token should raise InvalidTokenError!"
    except InvalidTokenError as exc:
        expected = "Authentication token is missing, empty, or not a string."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] Empty token rejected with exact message: '{exc.message}'")


def test_jwt_foreign_secret_rejection():
    print("\n--- [10] Testing Token Signed with Foreign Secret Key ---")
    foreign_key = "different_secret_key_that_is_at_least_32_bytes_long_12345"
    now = datetime.now(timezone.utc)
    foreign_token = jwt.encode(
        {"sub": "foreign-user", "type": "access", "exp": now + timedelta(hours=1), "iat": now, "nbf": now},
        foreign_key,
        algorithm="HS256",
    )
    
    try:
        decode_access_token(foreign_token)
        assert False, "Foreign token should fail signature verification!"
    except InvalidTokenError as exc:
        expected = "Token signature verification failed."
        assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
        print(f"  [PASS] Foreign secret token rejected with exact message: '{exc.message}'")


def test_security_configuration_guard():
    print("\n--- [11] Testing Missing Secret Key Guard ---")
    original_secret = config.JWT_SECRET_KEY
    expected = "JWT_SECRET_KEY is not configured or fails 256-bit security requirements. Please configure a valid secret in backend environment."
    try:
        config.JWT_SECRET_KEY = ""
        try:
            create_access_token({"sub": "test"})
            assert False, "Should raise SecurityConfigurationError when JWT_SECRET_KEY is empty!"
        except SecurityConfigurationError as exc:
            assert exc.status_code == 500
            assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
            print(f"  [PASS] create_access_token guarded with exact message: '{exc.message}'")
            
        try:
            decode_access_token("dummy.token.here")
            assert False, "Should raise SecurityConfigurationError when JWT_SECRET_KEY is empty!"
        except SecurityConfigurationError as exc:
            assert exc.status_code == 500
            assert exc.message == expected, f"Expected '{expected}', got '{exc.message}'"
            print(f"  [PASS] decode_access_token guarded with exact message: '{exc.message}'")
    finally:
        config.JWT_SECRET_KEY = original_secret


def main():
    print("=" * 75)
    print("RUNNING FINAL STEP 1 SECURITY FOUNDATION VERIFICATION AUDIT")
    print(f"Backend Directory: {config.BACKEND_DIR}")
    print(f"Enforced JWT Algorithm: {config.JWT_ALGORITHM}")
    print(f"Allowed JWT Algorithms: {config.ALLOWED_JWT_ALGORITHMS}")
    print(f"Configured JWT Expiration: {config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    print(f"Secret Configured: {'YES' if len(config.JWT_SECRET_KEY) >= 32 else 'NO'} (length={len(config.JWT_SECRET_KEY)} chars)")
    print("=" * 75)
    
    test_argon2id_hashing_and_verification()
    test_enforce_token_type_access_only()
    test_reject_boolean_claims_explicit_type_check()
    test_nbf_greater_than_exp_both_in_past()
    test_nbf_future_immature_and_missing()
    test_jwt_mandatory_claims_validation()
    test_jwt_strict_algorithm_enforcement()
    test_jwt_expired_token_handling()
    test_jwt_tampered_and_malformed_tokens()
    test_jwt_foreign_secret_rejection()
    test_security_configuration_guard()
    
    print("\n" + "=" * 75)
    print("ALL 11 FINAL SECURITY VERIFICATION SUITES PASSED (100% SUCCESS).")
    print("=" * 75)


if __name__ == "__main__":
    main()
