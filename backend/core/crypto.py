"""
Paddy Farming Assistant - Tenant Database Secret Encryption & Management Utility
Provides authenticated encryption for tenant database credentials stored at rest.
Uses Fernet (AES-128-CBC + HMAC-SHA256) with dedicated key management.
Prioritizes dedicated TENANT_ENCRYPTION_KEY from environment, with domain-separated HKDF-SHA256 fallback.
Ensures database passwords and encryption keys are never stored in the database or logged in plaintext.
"""

import base64
import os
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from app import config

logger = logging.getLogger(__name__)

# Domain separation context for tenant credential key derivation
TENANT_CREDENTIAL_HKDF_INFO = b"paddy_tenant_database_credentials_v1"
TENANT_CREDENTIAL_SALT = b"paddy_farming_assistant_db_salt"

_fernet_instance: Optional[Fernet] = None
_current_encryption_key: Optional[bytes] = None


class CredentialEncryptionError(Exception):
    """Raised when encryption or decryption of tenant credentials fails."""
    pass


def get_active_encryption_key() -> bytes:
    """
    Retrieves or derives the active Fernet encryption key.
    Prioritizes dedicated environment variable 'TENANT_ENCRYPTION_KEY'.
    Falls back to domain-separated HKDF key derivation from JWT_SECRET_KEY.
    Guarantees keys are never stored in database tables or logs.
    """
    global _current_encryption_key
    if _current_encryption_key is not None:
        return _current_encryption_key

    # 1. Check for explicit dedicated key in environment
    env_key = os.getenv("TENANT_ENCRYPTION_KEY")
    if env_key:
        try:
            key_bytes = env_key.strip().encode("utf-8")
            # Verify valid 32-byte base64 Fernet key
            Fernet(key_bytes)
            _current_encryption_key = key_bytes
            return _current_encryption_key
        except Exception as exc:
            logger.warning("TENANT_ENCRYPTION_KEY in environment is invalid: %s. Falling back to derived key.", exc)

    # 2. Derive key using HKDF-SHA256 with distinct domain salt
    secret = config.JWT_SECRET_KEY
    if not secret or len(secret) < 32:
        raise CredentialEncryptionError("JWT_SECRET_KEY is missing or fails 256-bit requirements.")

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=TENANT_CREDENTIAL_SALT,
        info=TENANT_CREDENTIAL_HKDF_INFO,
    )
    derived = hkdf.derive(secret.encode("utf-8"))
    _current_encryption_key = base64.urlsafe_b64encode(derived)
    return _current_encryption_key


def _get_fernet() -> Fernet:
    """Returns singleton Fernet cipher instance using active encryption key."""
    global _fernet_instance
    if _fernet_instance is None:
        key = get_active_encryption_key()
        _fernet_instance = Fernet(key)
    return _fernet_instance


def reset_encryption_key_cache():
    """Clears cached cipher and key (used during key rotation)."""
    global _fernet_instance, _current_encryption_key
    _fernet_instance = None
    _current_encryption_key = None


def encrypt_tenant_secret(plaintext_secret: str, key_override: Optional[bytes] = None) -> str:
    """
    Encrypts a tenant database secret into an authenticated ciphertext string.
    Plaintext secret is never logged or exposed.
    """
    if not plaintext_secret or not isinstance(plaintext_secret, str):
        raise CredentialEncryptionError("Tenant secret must be a non-empty string.")

    try:
        fernet = Fernet(key_override) if key_override else _get_fernet()
        ciphertext_bytes = fernet.encrypt(plaintext_secret.encode("utf-8"))
        return ciphertext_bytes.decode("utf-8")
    except Exception as exc:
        logger.error("Failed to encrypt tenant database secret: %s", exc)
        raise CredentialEncryptionError("Credential encryption failed.") from exc


def decrypt_tenant_secret(encrypted_token: str, key_override: Optional[bytes] = None) -> str:
    """
    Decrypts an authenticated ciphertext token back to plaintext database secret.
    Raises CredentialEncryptionError if ciphertext was tampered with or key is invalid.
    """
    if not encrypted_token or not isinstance(encrypted_token, str):
        raise CredentialEncryptionError("Encrypted token must be a non-empty string.")

    try:
        fernet = Fernet(key_override) if key_override else _get_fernet()
        plaintext_bytes = fernet.decrypt(encrypted_token.encode("utf-8"))
        return plaintext_bytes.decode("utf-8")
    except InvalidToken as exc:
        logger.error("Tenant database credential decryption failed: invalid key or tampered ciphertext.")
        raise CredentialEncryptionError("Invalid key or tampered credential ciphertext.") from exc
    except Exception as exc:
        logger.error("Unexpected error decrypting tenant database secret: %s", exc)
        raise CredentialEncryptionError("Credential decryption failed.") from exc


def reencrypt_tenant_secret(encrypted_token: str, old_key: bytes, new_key: bytes) -> str:
    """
    Re-encrypts a credential from an old key to a new key (Master Key Rotation).
    Used during master key rotation without changing PostgreSQL database passwords.
    """
    plaintext = decrypt_tenant_secret(encrypted_token, key_override=old_key)
    return encrypt_tenant_secret(plaintext, key_override=new_key)
