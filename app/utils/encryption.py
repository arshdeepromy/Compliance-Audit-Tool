"""Fernet symmetric encryption helpers for encrypting sensitive settings at rest.

Derives a Fernet key from the Flask app's SECRET_KEY using PBKDF2-HMAC-SHA256.
Used primarily for encrypting SMTP passwords stored in the database.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

logger = logging.getLogger(__name__)

# Fixed salt for key derivation — consistent across restarts.
# This is acceptable because the SECRET_KEY itself provides the entropy.
_DERIVATION_SALT = b"totika-smtp-fernet-key"


def _derive_fernet_key(secret_key: str) -> bytes:
    """Derive a 32-byte Fernet key from the app SECRET_KEY using PBKDF2."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        secret_key.encode("utf-8"),
        _DERIVATION_SALT,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(dk)


def get_fernet() -> Fernet:
    """Return a Fernet instance using the current app's SECRET_KEY."""
    secret_key = current_app.config["SECRET_KEY"]
    key = _derive_fernet_key(secret_key)
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string and return the ciphertext as a UTF-8 string."""
    f = get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str | None:
    """Decrypt a ciphertext string. Returns None if decryption fails."""
    try:
        f = get_fernet()
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception) as exc:
        logger.warning("Failed to decrypt value: %s", exc)
        return None
