"""Integration tests for dual-track authentication (cookie session + JWT Bearer)."""

from __future__ import annotations

import pytest


@pytest.fixture
def app():
    from app import create_app

    _app = create_app()
    _app.config["TESTING"] = True
    _app.config["WTF_CSRF_ENABLED"] = False
    return _app


@pytest.fixture
def client(app):
    return app.test_client()


class TestAuthMiddleware:
    def test_anonymous_request_sets_none_identity(self, client):
        resp = client.get("/api/v1/auth/whoami")
        assert resp.status_code == 401

    def test_bearer_jwt_sets_identity(self, client):
        from app.infrastructure.auth.jwt_token_service import create_access_token
        import os

        os.environ.setdefault("API_JWT_SECRET", "unit-test-secret-key-with-32-char-minimum")
        import app.core.runtime_config as rc

        rc._loaded = False
        rc._parser = None
        try:
            token, _ = create_access_token(user_id=42, username="testuser", role="viewer")
            resp = client.get(
                "/api/v1/auth/whoami",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["user_id"] == "42"
            assert data["auth_source"] in ("jwt", "jwt_cookie")
        finally:
            rc._loaded = False
            rc._parser = None