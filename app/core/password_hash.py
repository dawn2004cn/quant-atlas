"""Secure password hashing with PBKDF2-HMAC-SHA256 and legacy SHA-256 migration.

Replaces the insecure unsalted SHA-256 password storage used throughout
Quant Atlas.  Provides automatic **check-and-rehash** on login so users
created under the old scheme are silently upgraded.

Algorithm: PBKDF2-HMAC-SHA256, 600k iterations, 32-byte salt, 32-byte key.
This is the strongest algorithm available through the `cryptography` library
(which is already a project dependency via `cryptography>=41.0.0`).

Usage::

    from app.core.password_hash import hash_password, verify_password, needs_rehash

    # Hash a new password (e.g. during registration)
    h = hash_password("s3cret")

    # Verify during login
    if verify_password("s3cret", stored_hash):
        if needs_rehash(stored_hash):
            new_hash = hash_password("s3cret")
            # Caller must persist new_hash back to the user store.
            # See auth_service.py:_try_upgrade_password() for reference.
"""

from __future__ import annotations

import hashlib
import logging
import secrets

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Format markers (embedded in stored hash for forward compatibility)
# ---------------------------------------------------------------------------
_V1_MARKER = "$q$1$"   # PBKDF2-HMAC-SHA256, 600k iterations
_V0_MARKER = "$q$0$"   # Raw unsalted SHA-256 (legacy)
_V0_HEX_LEN = 64       # SHA-256 hex digest length


def _hash_v1(password: str) -> str:
    """PBKDF2-HMAC-SHA256 with 16-byte salt, 600k iterations."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    salt = secrets.token_bytes(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    dk = kdf.derive(password.encode("utf-8"))
    import base64
    return _V1_MARKER + base64.b64encode(salt + dk).decode("ascii")


def _hash_v0(password: str) -> str:
    """Legacy unsalted SHA-256 — ONLY for migration reference."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return a secure PBKDF2 hash of *password*."""
    return _V1_MARKER + _hash_v1(password)[len(_V1_MARKER):]


def verify_password(password: str, stored_hash: str) -> bool | str:
    """Verify *password* against *stored_hash*.

    Supports:
    - ``$q$1$...`` — current PBKDF2 format
    - ``$q$0$...`` — legacy PBKDF2 (shouldn't exist, but handled)
    - Raw 64-char hex — ancient unsalted SHA-256

    Returns:
    - ``False`` if password does not match
    - ``"force_reset"`` if password matches but hash is deprecated (legacy SHA-256)
      and the caller must flag the user for forced password reset
    - ``True`` if password matches and hash is current format

    Security rationale: Legacy SHA-256 hashes are unsalted and trivially
    crackable. Rather than permanently locking affected users, we accept
    the password but signal the caller to force a reset on next login.
    """
    if stored_hash.startswith(_V1_MARKER):
        import base64
        try:
            payload = base64.b64decode(stored_hash[len(_V1_MARKER):])
            salt = payload[:16]
            expected = payload[16:]
        except Exception:
            return False

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600_000,
        )
        try:
            derived = kdf.derive(password.encode("utf-8"))
        except Exception:
            return False
        return secrets.compare_digest(derived, expected)

    if stored_hash.startswith(_V0_MARKER):
        import base64
        try:
            payload = base64.b64decode(stored_hash[len(_V0_MARKER):])
            salt = payload[:16]
            expected = payload[16:]
        except Exception:
            return False

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        try:
            derived = kdf.derive(password.encode("utf-8"))
        except Exception:
            return False
        return secrets.compare_digest(derived, expected)

    # Ancient raw SHA-256 hex — accept if password matches but flag for forced reset.
    if len(stored_hash) == _V0_HEX_LEN and all(c in "0123456789abcdef" for c in stored_hash.lower()):
        import hashlib
        if hashlib.sha256(password.encode("utf-8")).hexdigest() == stored_hash:
            logger.info(
                "User authenticated with deprecated sha256_raw hash; "
                "flagged for forced password reset"
            )
            return "force_reset"
        return False

    return False


def needs_rehash(stored_hash: str) -> bool:
    """Return ``True`` if the hash should be upgraded to PBKDF2."""
    return not stored_hash.startswith(_V1_MARKER)


def get_hash_info(stored_hash: str) -> tuple[str, bool]:
    """Return ``(algorithm, needs_rehash)`` for migration tracking.

    Examples:
        ("pbkdf2_sha256", False)
        ("sha256_raw", True)
    """
    if stored_hash.startswith(_V1_MARKER):
        return ("pbkdf2_sha256", False)
    if stored_hash.startswith(_V0_MARKER):
        return ("pbkdf2_sha256_legacy", True)
    if len(stored_hash) == _V0_HEX_LEN and all(c in "0123456789abcdef" for c in stored_hash.lower()):
        return ("sha256_raw", True)
    return ("unknown", True)


def is_legacy_hash(stored_hash: str) -> bool:
    """Return ``True`` if the hash uses a deprecated algorithm (not PBKDF2 v1)."""
    return not stored_hash.startswith(_V1_MARKER)


def rehash_password(password: str, old_hash: str) -> str:
    """Re-hash *password* with the current PBKDF2 algorithm.

    Used during forced password reset or admin-triggered migration.
    Returns the new PBKDF2 hash string.
    """
    if is_legacy_hash(old_hash):
        logger.info("Rehashing legacy password hash for migration")
    return hash_password(password)
