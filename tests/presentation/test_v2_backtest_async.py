"""v2 backtest async query parameter tests."""

from __future__ import annotations

import werkzeug
from unittest.mock import MagicMock

import pytest
from flask import Flask

from app.presentation.api.routes_v2 import create_api_v2_blueprint

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"


def _v2_app(*, backtest_facade, auth_service):
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
        backtest_facade=backtest_facade,
        auth_service=auth_service,
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_JWT_SECRET", "unit-test-secret-key-with-32-chars-min")
    import app.core.runtime_config as runtime_config

    monkeypatch.setattr(runtime_config, "_loaded", False, raising=False)
    monkeypatch.setattr(runtime_config, "_parser", None, raising=False)

    auth_service = MagicMock()
    from app.domain.entities import UserAccount

    auth_service.authenticate.return_value = UserAccount(
        user_id=1,
        username="trader",
        role="trader",
        password_hash="x",
        avatar_url="",
    )

    app = Flask(__name__)
    app.secret_key = "test"
    app.config["TESTING"] = True
    from app.presentation.api.error_handlers import register_api_error_handlers

    register_api_error_handlers(app)
    facade = MagicMock()
    app.register_blueprint(_v2_app(backtest_facade=facade, auth_service=auth_service))
    http = app.test_client()
    token_resp = http.post("/api/v2/auth/token", json={"username": "trader", "password": "secret"})
    token = token_resp.get_json()["data"]["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}
    return http, facade, auth_header


def test_backtest_sync_by_default(client):
    http, facade, auth_header = client
    facade.run_backtest.return_value = {"status": "ok"}

    resp = http.post(
        "/api/v2/strategies/backtest",
        json={
            "symbol": "600519",
            "strategy": "MA",
            "start": "2024-01-01",
            "end": "2024-06-01",
        },
        headers=auth_header,
    )

    assert resp.status_code == 200
    facade.run_backtest.assert_called_once()
    facade.run_backtest_async.assert_not_called()


def test_backtest_async_when_query_flag_set(client):
    http, facade, auth_header = client
    facade.run_backtest_async.return_value = {"status": "queued", "task_id": "t-1"}

    resp = http.post(
        "/api/v2/strategies/backtest?async=1",
        json={
            "symbol": "600519",
            "strategy": "MA",
            "start": "2024-01-01",
            "end": "2024-06-01",
        },
        headers=auth_header,
    )

    assert resp.status_code == 200
    facade.run_backtest_async.assert_called_once()
    payload = resp.get_json()
    assert payload["data"]["status"] == "queued"
