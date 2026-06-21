"""v2 stock detail route uses StockApplicationService.get_stock_detail."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import werkzeug
from flask import Flask

from app.domain.enums import MarketCode
from app.presentation.api.routes_v2 import create_api_v2_blueprint

if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3.0.0"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        "app.presentation.api.v2.market.api_auth_required",
        lambda f: f,
    )

    stock_service = MagicMock()
    stock_service.get_stock_detail.return_value = SimpleNamespace(
        to_dict=lambda: {
            "code": "600519",
            "market": "CN",
            "profile": {"name": "贵州茅台", "realtime": {"price": 1700.0}},
            "indicators": {},
        }
    )

    app = Flask(__name__)
    app.secret_key = "test"
    app.config["TESTING"] = True
    from app.presentation.api.error_handlers import register_api_error_handlers

    register_api_error_handlers(app)
    app.register_blueprint(
        create_api_v2_blueprint(
            market_service=MagicMock(),
            stock_service=stock_service,
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
            backtest_facade=MagicMock(),
            auth_service=MagicMock(),
        )
    )
    http = app.test_client()
    return http, stock_service


def test_stock_detail_uses_get_stock_detail(client):
    http, stock_service = client
    resp = http.get("/api/v2/stocks/600519?market=CN")
    assert resp.status_code == 200
    stock_service.get_stock_detail.assert_called_once_with("600519", MarketCode.CN)
    body = resp.get_json()
    assert body["data"]["profile"]["name"] == "贵州茅台"
