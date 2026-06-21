"""Phase 50: attribution compare + trading preflight."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import werkzeug

from app.modules.strategy.services.analytics.attribution_compare_service import AttributionCompareService
from app.modules.execution.services.pre_trade_preflight_service import PreTradePreflightService
from app.domain.enums import MarketCode


def test_attribution_compare_builds_factor_rows() -> None:
    svc = AttributionCompareService()
    dto = svc.compare(base_symbol="600519", peer_symbol="000858", market=MarketCode.CN)
    assert dto.base_symbol == "600519"
    assert dto.peer_symbol == "000858"
    assert dto.factor_rows
    assert dto.summary


def test_attribution_compare_with_market_quotes() -> None:
    market = MagicMock()
    market.list_quotes.return_value = [
        {"code": "600519", "name": "贵州茅台", "change_pct": 2.5},
        {"code": "000858", "name": "五粮液", "change_pct": -1.2},
    ]
    svc = AttributionCompareService(market_service=market)
    dto = svc.compare(base_symbol="600519", peer_symbol="000858")
    assert dto.base_name == "贵州茅台"
    assert dto.peer_name == "五粮液"


def test_pre_trade_preflight_passes_small_order() -> None:
    svc = PreTradePreflightService()
    result = svc.preflight(symbol="600519", direction="BUY", price=100.0, quantity=10)
    assert result.passed is True
    assert result.allow_execute is True
    assert result.risk_score >= 50


def test_pre_trade_preflight_blocks_oversized_order() -> None:
    svc = PreTradePreflightService(validator=__import__(
        "app.infrastructure.trading.pre_trade_validator", fromlist=["PreTradeValidator"]
    ).PreTradeValidator(max_trade_amount=1000.0))
    result = svc.preflight(symbol="600519", direction="BUY", price=100.0, quantity=100)
    assert result.passed is False
    assert any(i.code == "trade_amount_exceeds_limit" for i in result.issues)


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


def test_attribution_compare_api(app_client) -> None:
    resp = app_client.get("/api/v1/attribution/compare?symbol=600519&peer=000858&market=CN")
    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert data.get("base_symbol") == "600519"
    assert data.get("factor_rows")


def test_trading_preflight_api(app_client) -> None:
    resp = app_client.post(
        "/api/v1/trading/preflight",
        json={"symbol": "600519", "direction": "BUY", "price": 50, "quantity": 100},
    )
    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert "risk_score" in data
    assert "passed" in data


def test_copilot_preflight_api(app_client) -> None:
    resp = app_client.get("/api/v1/strategy/copilot/preflight?symbol=600519&price=10&quantity=100")
    assert resp.status_code == 200
    assert (resp.get_json() or {}).get("data", {}).get("passed") is True
