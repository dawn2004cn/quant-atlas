"""API v2 JWT auth route tests."""

from __future__ import annotations

import werkzeug
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask

from app.domain.entities import UserAccount
from app.presentation.api.routes_v2 import create_api_v2_blueprint

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv("API_JWT_SECRET", "unit-test-secret-key-with-32-chars-min")
    import app.core.runtime_config as runtime_config

    monkeypatch.setattr(runtime_config, "_loaded", False, raising=False)
    monkeypatch.setattr(runtime_config, "_parser", None, raising=False)


def _minimal_v2_app(auth_service):
    auth = auth_service
    auth_svc = auth
    return create_api_v2_blueprint(
        market_service=MagicMock(),
        stock_service=MagicMock(),
        news_provider=MagicMock(),
        fundamental_access=MagicMock(),
        news_archive=MagicMock(),
        qlib_pipeline_service=MagicMock(),
        strategy_service=MagicMock(),
        pool_service=MagicMock(),
        ai_analysis_service=MagicMock(),
        ai_research_service=MagicMock(),
        analysis_service=MagicMock(),
        watchlist_service=MagicMock(),
        stock_group_service=MagicMock(),
        user_service=MagicMock(),
        rdagent_run_service=MagicMock(),
        prediction_service=MagicMock(),
        selection_source_service=MagicMock(),
        basic_market_data_service=MagicMock(),
        task_message_store=MagicMock(),
        auth_service=auth_svc,
    )


@pytest.fixture
def client():
    auth_service = MagicMock()
    auth_service.authenticate.return_value = UserAccount(
        user_id=42,
        username="trader1",
        role="trader",
        password_hash="x",
        avatar_url="",
    )
    app = Flask(__name__)
    app.secret_key = "test"
    app.config["TESTING"] = True
    from app.presentation.api.error_handlers import register_api_error_handlers

    register_api_error_handlers(app)
    app.register_blueprint(_minimal_v2_app(auth_service))
    return app.test_client(), auth_service


def test_issue_token_and_access_protected_route(client):
    http, auth_service = client
    resp = http.post("/api/v2/auth/token", json={"username": "trader1", "password": "secret"})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["ok"] is True
    token = payload["data"]["access_token"]
    auth_service.authenticate.assert_called_once()

    me = http.get("/api/v2/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    me_body = me.get_json()
    assert me_body["data"]["user_id"] == 42
    assert me_body["data"]["username"] == "trader1"


def test_protected_route_without_token_returns_403(client):
    http, _ = client
    resp = http.get("/api/v2/auth/me")
    assert resp.status_code == 403
