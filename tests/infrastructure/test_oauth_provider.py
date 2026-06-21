from __future__ import annotations

from app.infrastructure.auth.oauth_provider import NullOAuthProvider, build_oauth_provider


def test_build_oauth_provider_defaults_to_null_when_unconfigured(monkeypatch):
    monkeypatch.delenv("KEYCLOAK_SERVER_URL", raising=False)
    monkeypatch.delenv("KEYCLOAK_REALM", raising=False)
    monkeypatch.delenv("KEYCLOAK_CLIENT_ID", raising=False)
    monkeypatch.delenv("KEYCLOAK_CLIENT_SECRET", raising=False)

    provider = build_oauth_provider()
    assert isinstance(provider, NullOAuthProvider)
    assert provider.is_configured() is False
