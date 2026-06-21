"""JWT token service tests."""

from __future__ import annotations

import time

import pytest

from app.domain.exceptions import AuthorizationError, ValidationError
from app.infrastructure.auth.jwt_token_service import (
    create_access_token,
    decode_access_token,
    jwt_auth_enabled,
)


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv("API_JWT_SECRET", "unit-test-secret-key-with-32-chars-min")
    import app.core.runtime_config as runtime_config

    monkeypatch.setattr(runtime_config, "_loaded", False, raising=False)
    monkeypatch.setattr(runtime_config, "_parser", None, raising=False)


def test_jwt_roundtrip():
    assert jwt_auth_enabled() is True
    token, ttl = create_access_token(user_id=7, username="alice", role="viewer")
    assert ttl >= 60
    claims = decode_access_token(token)
    assert claims["sub"] == "7"
    assert claims["username"] == "alice"
    assert claims["role"] == "viewer"


def test_jwt_rejects_tampered_token():
    token, _ = create_access_token(user_id=1, username="bob", role="admin")
    bad = token[:-1] + ("a" if token[-1] != "a" else "b")
    with pytest.raises(AuthorizationError, match="invalid_token"):
        decode_access_token(bad)


def test_jwt_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("API_JWT_SECRET", "too-short")
    import app.core.runtime_config as runtime_config

    monkeypatch.setattr(runtime_config, "_loaded", False, raising=False)
    monkeypatch.setattr(runtime_config, "_parser", None, raising=False)
    with pytest.raises(ValidationError, match="at least"):
        create_access_token(user_id=1, username="bob", role="admin")


def test_jwt_rejects_expired_token(monkeypatch):
    import app.infrastructure.auth.jwt_token_service as jwt_mod

    base = int(time.time())
    monkeypatch.setattr(jwt_mod.time, "time", lambda: base)
    token, _ = create_access_token(user_id=1, username="bob", role="admin", ttl_seconds=1)
    monkeypatch.setattr(jwt_mod.time, "time", lambda: base + 120)
    with pytest.raises(AuthorizationError, match="token_expired"):
        decode_access_token(token)


def test_jwt_file_path_key_loading(monkeypatch, tmp_path):
    pk_pem = tmp_path / "jwt-private.pem"
    pub_pem = tmp_path / "jwt-public.pem"
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pk_pem.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ))
    pub_pem.write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ))

    import app.core.runtime_config as runtime_config
    monkeypatch.setattr(runtime_config, "_loaded", False, raising=False)
    monkeypatch.setattr(runtime_config, "_parser", None, raising=False)
    monkeypatch.setenv("API_JWT_ALG", "RS256")
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(pk_pem))
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", str(pub_pem))
    monkeypatch.delenv("API_JWT_SECRET", raising=False)
    monkeypatch.delenv("API_JWT_RSA_PRIVATE_KEY", raising=False)

    token, ttl = create_access_token(user_id=42, username="file_test", role="viewer")
    assert ttl >= 60
    claims = decode_access_token(token)
    assert claims["sub"] == "42"
    assert claims["username"] == "file_test"
