"""Fernet-based key encryption service for API keys and secrets.

Derives an encryption key from KEY_ENCRYPTION_KEY or FLASK_SECRET_KEY
environment variable.  Tokens include a version prefix to support
future algorithm rotation.

Usage:
    from app.core.key_encryption import KeyEncryptionService

    kms = KeyEncryptionService()
    token = kms.encrypt("my-secret-api-key")
    plaintext = kms.decrypt(token)
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.runtime_config import get_runtime

_VERSION = b"\x01"
_DEFAULT_SALT = b"quant-atlas-key-encrypt-v1"


def _encryption_salt() -> bytes:
    """Deployment salt; override via KEY_ENCRYPTION_SALT (changing it invalidates stored tokens)."""
    return get_runtime("KEY_ENCRYPTION_SALT", _DEFAULT_SALT.decode("ascii")).encode("utf-8")


class KeyEncryptionService:
    """Fernet symmetric encryption for sensitive stored credentials."""

    def __init__(self, secret_key: str | None = None):
        self._fernet = self._build_fernet(secret_key)

    @staticmethod
    def _build_fernet(secret_key: str | None) -> Fernet:
        """Derive a Fernet key from an env var or a direct secret_key."""
        raw = (
            os.environ.get("KEY_ENCRYPTION_KEY")
            or os.environ.get("FLASK_SECRET_KEY")
            or secret_key
            or ""
        )
        if not raw:
            raise ValueError(
                "KEY_ENCRYPTION_KEY or FLASK_SECRET_KEY must be set to use key encryption"
            )

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_encryption_salt(),
            iterations=480_000,
        )
        derived = kdf.derive(raw.encode("utf-8"))
        fernet_key = base64.urlsafe_b64encode(derived)
        return Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext secret, returning a versioned Fernet token."""
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return (_VERSION + token).decode("ascii")

    def decrypt(self, token: str) -> str:
        """Decrypt a versioned Fernet token back to plaintext."""
        raw = token.encode("ascii")
        version = raw[0:1]
        if version != _VERSION:
            raise ValueError(f"Unsupported encryption version: {version!r}")
        fernet_token = raw[1:]
        return self._fernet.decrypt(fernet_token).decode("utf-8")

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt raw bytes, returning version-prefixed token."""
        token = self._fernet.encrypt(data)
        return _VERSION + token

    def decrypt_bytes(self, token: bytes) -> bytes:
        """Decrypt version-prefixed token back to raw bytes."""
        if token[0:1] != _VERSION:
            raise ValueError(f"Unsupported encryption version: {token[0:1]!r}")
        return self._fernet.decrypt(token[1:]).decode("utf-8").encode("utf-8")


# Module-level singleton for convenience.
_key_service: KeyEncryptionService | None = None


def _get_key_service() -> KeyEncryptionService:
    global _key_service
    if _key_service is None:
        _key_service = KeyEncryptionService()
    return _key_service


def encrypt(secret: str) -> str:
    """Convenience: encrypt a secret string."""
    return _get_key_service().encrypt(secret)


def decrypt(token: str) -> str:
    """Convenience: decrypt a token string."""
    return _get_key_service().decrypt(token)
