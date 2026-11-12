"""
Paddy Farming Assistant - Security & Authentication Foundation (STEP 1)
Provides Argon2id password hashing/verification and PyJWT token creation/decoding.
Strictly decoupled from database tables, routes, and AI inference models.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import argon2
from argon2 import PasswordHasher, Type
import jwt

from app import config
from app.exceptions import (
    TokenExpiredError,
    InvalidTokenError,
    SecurityConfigurationError,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# Security Policy Constants
# ==============================================================================
# Strictly approved signing algorithm per project architecture standards
APPROVED_JWT_ALGORITHM: str = "HS256"
ALLOWED_JWT_ALGORITHMS: List[str] = [APPROVED_JWT_ALGORITHM]

# Standard token type identifier for access tokens
TOKEN_TYPE_ACCESS: str = "access"

# ==============================================================================
# Argon2id Password Hasher Configuration (RFC 9106 / OWASP Recommended)
# ==============================================================================
# - Type.ID: Argon2id hybrid (side-channel and GPU-resistance)
# - time_cost=3: 3 iterations
# - memory_cost=65536: 64 MiB RAM usage
# - parallelism=4: 4 concurrent lanes
# - hash_len=32: 32 bytes derived key
# - salt_len=16: 16 bytes cryptographically secure random salt
# ==============================================================================
_argon2_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using Argon2id with OWASP-recommended parameters.
    
    Args:
        password: Plaintext password to hash.
        
    Returns:
        Argon2id encoded hash string (e.g., '$argon2id$v=19$m=65536,t=3,p=4$...').
        
    Raises:
        ValueError: If password is empty or not a string.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    return _argon2_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against an Argon2id hash.
    
    Args:
        plain_password: The plaintext candidate password.
        hashed_password: The stored Argon2id hash.
        
    Returns:
        True if the password matches the hash, False otherwise.
    """
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    if not plain_password or not hashed_password:
        return False

    try:
        return _argon2_hasher.verify(hashed_password, plain_password)
    except argon2.exceptions.VerifyMismatchError:
        return False
    except argon2.exceptions.VerificationError:
        logger.warning("Argon2 verification failed due to verification error.")
        return False
    except argon2.exceptions.InvalidHashError:
        logger.warning("Argon2 verification failed: malformed or invalid hash format.")
        return False
    except Exception as exc:
        logger.error("Unexpected error during Argon2 password verification: %s", exc)
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Checks whether a stored hash was created with older/weaker parameters
    and should be re-hashed on successful login.
    """
    try:
        return _argon2_hasher.check_needs_rehash(hashed_password)
    except Exception:
        return True


# ==============================================================================
# PyJWT Token Management (Strict HS256 & Strict Mandatory Claims Validation)
# ==============================================================================

def _get_validated_secret_key() -> str:
    """
    Validates and retrieves the JWT signing key from configuration.
    Enforces minimum 256-bit (32 character) key length.
    Never logs or exposes the secret key.
    
    Raises:
        SecurityConfigurationError: If JWT_SECRET_KEY is missing, empty, or shorter than 32 chars.
    """
    secret = config.JWT_SECRET_KEY
    if not secret or not isinstance(secret, str) or len(secret.strip()) < 32:
        logger.critical(
            "JWT_SECRET_KEY is missing, empty, or shorter than 32 characters (256-bit). "
            "Refusing to generate or verify authentication tokens."
        )
        raise SecurityConfigurationError(
            "JWT_SECRET_KEY is not configured or fails 256-bit security requirements. "
            "Please configure a valid secret in backend environment."
        )
    return secret.strip()


def _is_valid_timestamp(val: Any) -> bool:
    """
    Validates that a claim value is a genuine numeric timestamp (int or float) and NOT a boolean.
    In Python, bool is a subclass of int (isinstance(True, int) is True), so an explicit
    bool rejection guard is mandatory.
    """
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Creates a signed JSON Web Token (JWT) strictly for access authentication.
    Strictly enforces token_type='access'. Does not allow arbitrary token types.
    Strictly uses the approved HS256 algorithm.
    
    Args:
        data: Payload claims to embed in the token. MUST contain a non-empty string 'sub'.
        expires_delta: Optional custom token expiration duration. If omitted,
                       defaults to config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES.
                       
    Returns:
        Encoded JWT access token string.
        
    Raises:
        ValueError: If data is empty, not a dict, missing valid 'sub',
                    or attempts to pass an unapproved 'type' claim.
        SecurityConfigurationError: If JWT_SECRET_KEY is missing or invalid.
    """
    if not isinstance(data, dict) or not data:
        raise ValueError("Token payload data must be a non-empty dictionary.")

    sub = data.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise ValueError("Token payload must contain a non-empty string 'sub' claim.")

    # Strictly enforce that this function only creates access tokens
    if "type" in data and data["type"] != TOKEN_TYPE_ACCESS:
        raise ValueError(
            f"create_access_token() strictly creates '{TOKEN_TYPE_ACCESS}' tokens. "
            f"Conflicting type '{data['type']}' is forbidden."
        )

    secret_key = _get_validated_secret_key()
    algorithm = APPROVED_JWT_ALGORITHM

    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    # Strictly enforce type='access' and timestamp claims
    to_encode.update({
        "sub": sub.strip(),
        "type": TOKEN_TYPE_ACCESS,
        "exp": expire,
        "iat": now,
        "nbf": now,
    })

    try:
        return jwt.encode(to_encode, secret_key, algorithm=algorithm)
    except Exception as exc:
        logger.error("Failed to generate JWT access token: %s", exc)
        raise


def decode_access_token(
    token: str,
    expected_token_type: str = TOKEN_TYPE_ACCESS,
) -> Dict[str, Any]:
    """
    Decodes, cryptographically verifies, and validates an access JWT token.
    Strictly enforces:
    - Approved algorithm: HS256 (rejects algorithm confusion)
    - Valid cryptographic signature
    - Mandatory claims present: 'sub', 'exp', 'iat', 'nbf', 'type'
    - Strict rejection of boolean values for 'exp', 'iat', and 'nbf' via explicit type checks
    - Semantic cross-claim consistency (nbf <= exp, iat <= exp) evaluated independently
    - Valid token type ('access')
    - Valid temporal window (nbf <= now, exp >= now)
    
    Args:
        token: Encoded JWT string.
        expected_token_type: Expected 'type' claim value (default: 'access').
        
    Returns:
        Decoded payload dictionary with verified claims.
        
    Raises:
        TokenExpiredError: If token expiration (exp) is in the past.
        InvalidTokenError: If token signature is invalid, malformed, not yet valid (nbf),
                           missing mandatory claims, contains boolean/non-numeric timestamps,
                           or has invalid/inconsistent claims.
        SecurityConfigurationError: If JWT_SECRET_KEY is missing or invalid.
    """
    if not isinstance(token, str) or not token.strip():
        raise InvalidTokenError("Authentication token is missing, empty, or not a string.")

    secret_key = _get_validated_secret_key()

    # 1. Cryptographic signature and structural decode via PyJWT
    # verify_exp, verify_nbf, verify_iat are validated in explicit stages below
    # to ensure boolean values are caught by explicit strict type validation,
    # and semantic checks (nbf > exp) are independently evaluated.
    try:
        payload = jwt.decode(
            token.strip(),
            secret_key,
            algorithms=ALLOWED_JWT_ALGORITHMS,
            options={
                "verify_signature": True,
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
                "require": ["exp", "iat", "sub", "nbf"],
            },
        )
    except jwt.InvalidSignatureError as exc:
        logger.warning("Security alert: JWT signature verification failed.")
        raise InvalidTokenError("Token signature verification failed.") from exc

    except jwt.DecodeError as exc:
        logger.warning("Authentication rejected: Malformed or undecodable JWT token.")
        raise InvalidTokenError("Malformed or undecodable authentication token.") from exc

    except jwt.InvalidAlgorithmError as exc:
        logger.warning("Security alert: JWT signed with unapproved algorithm.")
        raise InvalidTokenError("Token signed with an unapproved algorithm.") from exc

    except jwt.MissingRequiredClaimError as exc:
        logger.warning("Authentication rejected: Missing mandatory JWT claim [%s]", exc)
        raise InvalidTokenError(f"Missing mandatory token claim: {exc}") from exc

    except jwt.InvalidTokenError as exc:
        logger.warning("Authentication rejected: Invalid JWT token [%s]", exc)
        raise InvalidTokenError(f"Invalid authentication token: {exc}") from exc

    # 2. Strict Type Validation of Mandatory Claims (Boolean Rejection Guards)
    # a. Validate 'sub' claim
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise InvalidTokenError("Token 'sub' claim must be a non-empty string.")

    # b. Validate 'exp' claim (strictly numeric, rejecting boolean)
    exp = payload.get("exp")
    if not _is_valid_timestamp(exp):
        raise InvalidTokenError("Token 'exp' claim must be a numeric timestamp (excluding boolean).")

    # c. Validate 'iat' claim (strictly numeric, rejecting boolean)
    iat = payload.get("iat")
    if not _is_valid_timestamp(iat):
        raise InvalidTokenError("Token 'iat' claim must be a numeric timestamp (excluding boolean).")

    # d. Validate 'nbf' claim (strictly numeric, rejecting boolean)
    nbf = payload.get("nbf")
    if not _is_valid_timestamp(nbf):
        raise InvalidTokenError("Token 'nbf' claim must be a numeric timestamp (excluding boolean).")

    # e. Validate 'type' claim (must be string and match expected_token_type)
    token_type = payload.get("type")
    if token_type is None:
        raise InvalidTokenError("Token 'type' claim is missing.")
    if not isinstance(token_type, str):
        raise InvalidTokenError("Token 'type' claim must be a string.")
    if token_type != expected_token_type:
        raise InvalidTokenError(
            f"Invalid token type '{token_type}'. Expected '{expected_token_type}'."
        )

    # 3. Semantic Cross-Claim Validation (Evaluated independently before temporal checks)
    if nbf > exp:
        raise InvalidTokenError("Token 'nbf' claim cannot be later than 'exp' claim.")
    if iat > exp:
        raise InvalidTokenError("Token 'iat' claim cannot be later than 'exp' claim.")

    # 4. Temporal Validation (Against Current Time)
    now_ts = datetime.now(timezone.utc).timestamp()
    if nbf > now_ts:
        logger.info("Authentication rejected: JWT token is not yet valid (nbf in future).")
        raise InvalidTokenError("Authentication token is not yet valid (nbf in future).")
    if exp < now_ts:
        logger.info("Authentication rejected: JWT token has expired.")
        raise TokenExpiredError("Authentication token has expired. Please log in again.")

    return payload
