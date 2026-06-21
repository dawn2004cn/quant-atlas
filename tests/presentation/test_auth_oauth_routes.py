"""Auth blueprint OAuth route tests."""

from __future__ import annotations

import werkzeug
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"  # Flask test_client compat on werkzeug 3.1+

from app.infrastructure.auth.oauth_provider import NullOAuthProvider, extract_subject_from_token_response
from app.presentation.web.auth import create_auth_blueprint


class _OAuthStub:
    def is_configured(self) -> bool:
        return True

    def authorization_url(self, redirect_uri: str, state: str) -> str:
        return f"https://idp.example/auth?redirect_uri={redirect_uri}&state={state}"

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        return {"access_token": "tok-1"}

    def introspect(self, access_token: str) -> dict:
        return {"sub": "kc-user-1", "email": "user@example.com", "active": True}


@pytest.fixture
def auth_app(tmp_path):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True

    from app.infrastructure.repositories.common.json_repositories import JsonUserRepository
    from app.modules.user.services.user.auth_service import AuthService
    from app.modules.user.services.user.user_service import UserApplicationService

    repo = JsonUserRepository(tmp_path / "users.json")
    auth_service = AuthService(user_repository=repo)
    user_service = UserApplicationService(repository=repo, auth_service=auth_service)
    settings = SimpleNamespace(
        wechat_open_app_id="",
        wechat_open_app_secret="",
        wechat_redirect_uri="",
    )

    bp = create_auth_blueprint(
        auth_service=auth_service,
        user_service=user_service,
        app_settings=settings,
        oauth_provider=_OAuthStub(),
    )
    app.register_blueprint(bp)
    return app


def test_oauth_start_redirects_to_idp(auth_app):
    client = auth_app.test_client()
    resp = client.get("/auth/oauth/start")
    assert resp.status_code == 302
    assert "idp.example" in resp.headers["Location"]


def test_oauth_start_unconfigured_redirects_login():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True
    settings = SimpleNamespace(
        wechat_open_app_id="",
        wechat_open_app_secret="",
        wechat_redirect_uri="",
    )
    bp = create_auth_blueprint(
        auth_service=MagicMock(),
        user_service=MagicMock(),
        app_settings=settings,
        oauth_provider=NullOAuthProvider(),
    )
    app.register_blueprint(bp)
    resp = app.test_client().get("/auth/oauth/start", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_extract_subject_from_token_response():
    provider = _OAuthStub()
    sub, name = extract_subject_from_token_response(provider, {"access_token": "tok-1"})
    assert sub == "kc-user-1"
    assert name == "user@example.com"
