from __future__ import annotations

"""HMAC-signed share tokens with expiry for read-only evidence links."""

import hashlib
import hmac
import time
from datetime import datetime, timedelta


def generate_share_token(
    resource_id: str,
    *,
    secret: str,
    ttl_days: int = 7,
) -> tuple[str, datetime]:
    """Return (token, expires_at)."""
    expires_at = datetime.utcnow() + timedelta(days=max(1, ttl_days))
    exp_unix = int(expires_at.timestamp())
    payload = f"{resource_id}.{exp_unix}"
    sig = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:20]
    return f"{payload}.{sig}", expires_at


def verify_share_token(token: str, *, secret: str) -> str | None:
    """Validate token; return resource_id if valid and not expired."""
    parts = (token or "").strip().split(".")
    if len(parts) != 3:
        return None
    resource_id, exp_raw, sig = parts
    payload = f"{resource_id}.{exp_raw}"
    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:20]
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        if time.time() > int(exp_raw):
            return None
    except ValueError:
        return None
    return resource_id
