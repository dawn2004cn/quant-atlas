from __future__ import annotations

from datetime import datetime, timedelta

from app.core.secure_share_token import generate_share_token, verify_share_token


def test_generate_and_verify_roundtrip() -> None:
    secret = "test-secret-key"
    snap_id = "snap-abc123"
    token, expires_at = generate_share_token(snap_id, secret=secret, ttl_days=3)
    assert isinstance(expires_at, datetime)
    assert verify_share_token(token, secret=secret) == snap_id


def test_verify_rejects_wrong_secret() -> None:
    token, _ = generate_share_token("snap-x", secret="alpha", ttl_days=1)
    assert verify_share_token(token, secret="beta") is None


def test_verify_rejects_expired_token() -> None:
    secret = "k"
    snap_id = "snap-old"
    expires_at = datetime.utcnow() - timedelta(days=1)
    exp_unix = int(expires_at.timestamp())
    import hashlib
    import hmac

    payload = f"{snap_id}.{exp_unix}"
    sig = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:20]
    token = f"{payload}.{sig}"
    assert verify_share_token(token, secret=secret) is None
