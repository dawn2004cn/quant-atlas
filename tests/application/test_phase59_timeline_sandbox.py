"""Phase 59: attribution timeline and strategy sensitivity sandbox."""

from __future__ import annotations

from pathlib import Path

import pytest
import werkzeug

from app.modules.strategy.services.strategy.sensitivity_sandbox_service import (
    SensitivitySandboxService,
)
from app.modules.system.services.ui.attribution_timeline_service import (
    AttributionTimelineService,
)
from app.domain.enums import MarketCode


class FakeNewsArchive:
    def list_for_symbol(self, market: str, symbol: str, *, limit: int):
        assert market == "CN"
        assert symbol == "600519"
        return [{"published_at": "2026-05-20 09:30", "title": "earnings beat"}]


class FakeFundamentals:
    def cn_research_reports(self, symbol: str, *, limit: int):
        assert symbol == "600519"
        return ([{"date": "2026-05-21", "title": "broker upgrade"}], None)


class FakeBasicMarketData:
    def longhu_for_stock(self, symbol: str, *, limit: int):
        assert symbol == "600519"
        return [{"trade_date": "2026-05-22", "reason": "large order activity"}]


class FakeStockHistory:
    def get_history(self, symbol: str, market: MarketCode, start: str, end: str):
        assert market == MarketCode.CN
        return [
            {"date": "2026-05-19", "close": 10, "volume": 100, "amount": 1000},
            {"date": "2026-05-20", "close": 11, "volume": 1000, "amount": 200000000},
        ]


def test_attribution_timeline_merges_evidence_lanes() -> None:
    payload = AttributionTimelineService(
        stock_service=FakeStockHistory(),
        news_archive=FakeNewsArchive(),
        fundamental_access=FakeFundamentals(),
        basic_market_data_service=FakeBasicMarketData(),
    ).build_timeline(
        "600519",
        MarketCode.CN,
        start="2026-05-18",
        end="2026-05-23",
    )

    types = {item["type"] for item in payload["markers"]}
    assert {"news", "research_report", "large_order", "price_move", "volume_spike"} <= types
    assert payload["summary"]["has_evidence"] is True


def test_sensitivity_sandbox_penalizes_negative_market_shock() -> None:
    result = {
        "volatility": 6.0,
        "trend": "uptrend",
        "regime": "high_volatility_bullish",
        "recommendations": [
            {"strategy": "momentum", "score": 0.8},
            {"strategy": "grid_trading", "score": 0.7},
        ],
    }

    sandbox = SensitivitySandboxService().simulate(
        result,
        market_shock_pct=-1.0,
        volatility_threshold=5.0,
        stop_loss_pct=4.0,
    )

    by_strategy = {item["strategy"]: item for item in sandbox["strategies"]}
    assert by_strategy["momentum"]["adjusted_score"] < by_strategy["momentum"]["base_score"]
    assert sandbox["top_pick"]["strategy"] in {"momentum", "grid_trading"}


@pytest.fixture
def app_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("ENABLE_BACKGROUND_SCANNER", "0")
    monkeypatch.setenv("ENABLE_BASIC_DATA_SCHEDULER", "0")
    monkeypatch.setenv("ENABLE_CELERY", "0")
    monkeypatch.setenv("ENABLE_QLIB", "0")
    monkeypatch.setenv("ENABLE_RD_AGENT", "0")
    monkeypatch.setenv("TASK_MESSAGE_REDIS_URL", "memory://")
    if not hasattr(werkzeug, "__version__"):
        monkeypatch.setattr(werkzeug, "__version__", "3.0.0", raising=False)

    instance = tmp_path / "instance"
    instance.mkdir()
    monkeypatch.setattr("app.config.settings.INSTANCE_DIR", instance)

    from app.bootstrap import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert login.status_code in (302, 303)
    return client


def test_strategy_copilot_api_returns_sandbox(monkeypatch: pytest.MonkeyPatch, app_client) -> None:
    class FakeUseCase:
        def execute(self, symbol: str, market: MarketCode):
            return {
                "symbol": symbol,
                "volatility": 6.0,
                "trend": "uptrend",
                "regime": "high_volatility_bullish",
                "recommendations": [{"strategy": "momentum", "score": 0.8}],
            }

    monkeypatch.setattr(
        "app.application.use_cases.strategy_copilot_use_case.get_strategy_copilot_use_case",
        lambda: FakeUseCase(),
    )

    resp = app_client.get(
        "/api/v1/strategy/copilot?symbol=600519&market=CN&market_shock_pct=-1"
    )
    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert "sensitivity_sandbox" in data
    assert data["sensitivity_sandbox"]["inputs"]["market_shock_pct"] == -1.0
