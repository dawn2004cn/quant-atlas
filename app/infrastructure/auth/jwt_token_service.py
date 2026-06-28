"""HS256/RS256 JWT helpers for API Bearer authentication.

Supports key rotation via API_JWT_KEY_VERSIONS (comma-separated base64 keys
with optional :version suffix).  Defaults to HS256; set API_JWT_ALG=RS256
to use asymmetric signatures.

RS256 keys are loaded from (in priority order):
  1. File paths: JWT_PRIVATE_KEY_PATH / JWT_PUBLIC_KEY_PATH (PEM files on disk)
  2. Environment variables: API_JWT_RSA_PRIVATE_KEY / API_JWT_RSA_PUBLIC_KEYS
     (Base64-encoded PEM content, with optional :version suffix for rotation)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.domain.exceptions import AuthorizationError, ValidationError

logger = get_logger(__name__)

_DEFAULT_TTL = 3600
_DEFAULT_KEY_VERSION = "1"
_REFRESH_TTL = 604800  # 7 days
_ACCESS_TOKEN_TYPE = "access"
_REFRESH_TOKEN_TYPE = "refresh"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def jwt_auth_enabled() -> bool:
    if bool(get_runtime("API_JWT_SECRET", "").strip()):
        return True
    if bool(get_runtime("API_JWT_RSA_PRIVATE_KEY", "").strip()):
        return True
    if bool(get_runtime("API_JWT_RSA_PUBLIC_KEYS", "").strip()):
        return True
    return False


def _jwt_alg() -> str:
    return (get_runtime("API_JWT_ALG") or "HS256").strip().upper()


def _jwt_key_versions() -> dict[str, bytes]:
    raw = (get_runtime("API_JWT_KEY_VERSIONS") or "").strip()
    versions: dict[str, bytes] = {}
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                key_b64, ver = part.rsplit(":", 1)
            else:
                key_b64 = part
                ver = _DEFAULT_KEY_VERSION
            try:
                versions[ver.strip()] = base64.b64decode(key_b64.strip())
            except Exception as exc:
                logger.warning("Failed to parse JWT key version '%s': %s", ver, exc)
    if not versions:
        secret = (get_runtime("API_JWT_SECRET") or "").strip()
        if secret:
            versions[_DEFAULT_KEY_VERSION] = secret.encode("utf-8")
    return versions


_MIN_JWT_SECRET_LEN = 32


def _jwt_secret() -> str:
    secret = (get_runtime("API_JWT_SECRET") or "").strip()
    if not secret:
        raise ValidationError("API JWT is not configured (set API_JWT_SECRET)")
    if len(secret) < _MIN_JWT_SECRET_LEN:
        raise ValidationError(
            f"API_JWT_SECRET must be at least {_MIN_JWT_SECRET_LEN} characters"
        )
    return secret


def _jwt_ttl_seconds() -> int:
    raw = get_runtime("API_JWT_TTL_SECONDS", str(_DEFAULT_TTL))
    try:
        ttl = int(raw)
    except (TypeError, ValueError):
        ttl = _DEFAULT_TTL
    return max(60, min(ttl, 86400))


def _active_key_version() -> str:
    versions = _jwt_key_versions()
    if not versions:
        return _DEFAULT_KEY_VERSION
    return sorted(versions.keys(), key=lambda v: int(v) if v.isdigit() else 0)[-1]


def _load_rsa_private_key() -> Any:
    key_path = (get_runtime("JWT_PRIVATE_KEY_PATH") or "").strip()
    if key_path:
        pem_path = Path(key_path)
        if pem_path.exists():
            pem_bytes = pem_path.read_bytes()
            try:
                return serialization.load_pem_private_key(
                    pem_bytes, password=None, backend=default_backend()
                )
            except Exception as exc:
                raise ValidationError(f"Failed to load RSA private key from {key_path}: {exc}") from exc
        raise ValidationError(f"JWT_PRIVATE_KEY_PATH={key_path} but file not found")
    raw = (get_runtime("API_JWT_RSA_PRIVATE_KEY") or "").strip()
    if not raw:
        raise ValidationError("RS256 selected but API_JWT_RSA_PRIVATE_KEY is not set")
    try:
        pem_bytes = base64.b64decode(raw)
        return serialization.load_pem_private_key(
            pem_bytes, password=None, backend=default_backend()
        )
    except Exception as exc:
        raise ValidationError(f"Failed to load RSA private key: {exc}") from exc


def _load_rsa_public_key(pem_base64: str) -> Any:
    try:
        pem_bytes = base64.b64decode(pem_base64.strip())
        return serialization.load_pem_public_key(pem_bytes, backend=default_backend())
    except Exception as exc:
        logger.warning("Failed to load RSA public key: %s", exc)
        return None


def _load_public_key_from_path() -> Any | None:
    key_path = (get_runtime("JWT_PUBLIC_KEY_PATH") or "").strip()
    if not key_path:
        return None
    pem_path = Path(key_path)
    if not pem_path.exists():
        logger.warning("JWT_PUBLIC_KEY_PATH=%s but file not found", key_path)
        return None
    try:
        pem_bytes = pem_path.read_bytes()
        return serialization.load_pem_public_key(pem_bytes, backend=default_backend())
    except Exception as exc:
        logger.warning("Failed to load RSA public key from %s: %s", key_path, exc)
        return None


def _rsa_public_key_versions() -> dict[str, Any]:
    versions: dict[str, Any] = {}
    file_pub = _load_public_key_from_path()
    if file_pub is not None:
        versions[_DEFAULT_KEY_VERSION] = file_pub
        return versions
    raw = (get_runtime("API_JWT_RSA_PUBLIC_KEYS") or "").strip()
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                pem_b64, ver = part.rsplit(":", 1)
            else:
                pem_b64 = part
                ver = _DEFAULT_KEY_VERSION
            pub = _load_rsa_public_key(pem_b64.strip())
            if pub is not None:
                versions[ver.strip()] = pub
    if not versions:
        try:
            priv = _load_rsa_private_key()
            versions[_DEFAULT_KEY_VERSION] = priv.public_key()
        except Exception:
            pass
    return versions


def create_access_token(
    *,
    user_id: int,
    username: str,
    role: str,
    ttl_seconds: int | None = None,
) -> tuple[str, int]:
    alg = _jwt_alg()
    ttl = ttl_seconds if ttl_seconds is not None else _jwt_ttl_seconds()
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "v": _active_key_version(),
        "type": _ACCESS_TOKEN_TYPE,
    }
    if alg == "RS256":
        return _rs256_sign(payload, ttl)
    secret = _jwt_secret()
    header = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}"
    signature = _b64url_encode(
        hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    )
    return f"{signing_input}.{signature}", ttl


def create_refresh_token(
    *,
    user_id: int,
    username: str,
    role: str,
    ttl_seconds: int | None = None,
) -> tuple[str, int]:
    """Create a long-lived refresh token (default 7 days)."""
    ttl = ttl_seconds if ttl_seconds is not None else _REFRESH_TTL
    alg = _jwt_alg()
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "v": _active_key_version(),
        "type": _REFRESH_TOKEN_TYPE,
    }
    if alg == "RS256":
        return _rs256_sign(payload, ttl)
    secret = _jwt_secret()
    header = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}"
    signature = _b64url_encode(
        hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    )
    return f"{signing_input}.{signature}", ttl


def _rs256_sign(payload: dict, ttl: int) -> tuple[str, int]:
    priv = _load_rsa_private_key()
    header = _b64url_encode(
        json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}"
    sig = priv.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{_b64url_encode(sig)}", ttl


def decode_access_token(token: str) -> dict[str, Any]:
    parts = (token or "").split(".")
    if len(parts) != 3:
        raise AuthorizationError("invalid_token")
    header_b64, payload_b64, signature_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64))
    except Exception:
        raise AuthorizationError("invalid_token") from None
    if not isinstance(header, dict):
        raise AuthorizationError("invalid_token")
    token_alg = str(header.get("alg", "HS256")).upper()
    signing_input = f"{header_b64}.{payload_b64}"
    if token_alg == "RS256":
        payload = _rs256_verify(signing_input, signature_b64)
    else:
        payload = _hs256_verify(signing_input, signature_b64, payload_b64)
    if payload is None:
        raise AuthorizationError("invalid_token")
    if not isinstance(payload, dict):
        raise AuthorizationError("invalid_token")
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or int(exp) < int(time.time()):
        raise AuthorizationError("token_expired")
    if not str(payload.get("sub") or "").strip():
        raise AuthorizationError("invalid_token")
    # Phase 5: JWT blacklist check
    jti = payload.get("jti")
    if jti:
        from app.infrastructure.auth.jwt_blacklist import is_token_revoked
        if is_token_revoked(str(jti)):
            raise AuthorizationError("token_revoked")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a refresh token (must have type=refresh)."""
    payload = decode_access_token(token)
    if payload.get("type") != _REFRESH_TOKEN_TYPE:
        raise AuthorizationError("invalid_token_type")
    return payload


def _rs256_verify(signing_input: str, signature_b64: str) -> dict | None:
    payload = None
    for _ver, pub_key in _rsa_public_key_versions().items():
        try:
            sig_bytes = _b64url_decode(signature_b64)
            pub_key.verify(
                sig_bytes, signing_input.encode(), padding.PKCS1v15(), hashes.SHA256()
            )
            _, pb = signing_input.split(".", 1)
            payload = json.loads(_b64url_decode(pb))
            break
        except Exception:
            continue
    return payload


def _hs256_verify(
    signing_input: str, signature_b64: str, payload_b64: str
) -> dict | None:
    payload = None
    for _ver, key_bytes in _jwt_key_versions().items():
        expected = _b64url_encode(
            hmac.new(key_bytes, signing_input.encode(), hashlib.sha256).digest()
        )
        if hmac.compare_digest(expected, signature_b64):
            try:
                payload = json.loads(_b64url_decode(payload_b64))
            except (json.JSONDecodeError, ValueError) as exc:
                raise AuthorizationError("invalid_token") from exc
            break
    return payload
