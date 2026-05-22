"""
Encryption service using Fernet (AES-128-CBC + HMAC-SHA256).

The ENCRYPTION_KEY env var must be a 32-byte hex string, e.g.:
    python -c "import secrets; print(secrets.token_hex(32))"

Fernet derives its 32-byte key from the first 32 bytes of our hex secret
converted to raw bytes (= 16 bytes) – we therefore use PBKDF2 to stretch
the user-supplied key to exactly 32 bytes, which Fernet expects as
url-safe base64.
"""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _build_fernet() -> Fernet:
    """
    Derive a 32-byte Fernet key from the configured ENCRYPTION_KEY.
    Uses SHA-256 so the user can supply any non-empty string as key.
    """
    raw_key = settings.encryption_key.encode()
    if not raw_key:
        # Fallback for local dev without a key set – NOT safe for production
        raw_key = b"dev-only-insecure-key-do-not-use"

    # SHA-256 always gives 32 bytes → perfect for Fernet
    derived = hashlib.sha256(raw_key).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


# Module-level singleton – built once on import
_fernet: Fernet = _build_fernet()


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return a base64-encoded Fernet token."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """
    Decrypt a Fernet token back to plaintext.
    Raises ValueError if the token is invalid or was encrypted with a
    different key.
    """
    try:
        return _fernet.decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Decryption failed – wrong ENCRYPTION_KEY or corrupted data."
        ) from exc
