"""Phase 58: intent-aware discovery and user decision context."""

from __future__ import annotations

from pathlib import Path

import pytest
import werkzeug

from app.modules.system.services.ui.stock_discovery_service import StockDiscoveryService
from app.modules.system.services.ui.user_decision_context_service import UserDecisionContextService
from app.domain.enums import MarketCode


class FakeStockService:
    def search_stocks(self, query: str, *, limit: int, market: MarketCode):
        assert market == MarketCode.CN
        rows = {
            "power": [
                {
                    "symbol": "600900",
                    "name": "Power Utility",
                    "industry": "power",
                    "pb": 0.8,
                }
            ],
            "银行": [{"symbol": "600000", "name": "Bank", "industry": "bank", "pb": 0.9}],
        }
        return rows.get(query, [])[:limit]


def test_stock_discovery_parses_tags_and_annotates_matches() -> None:
    svc = StockDiscoveryService(FakeStockService())
    payload = svc.discover("power + low pb", market=MarketCode.CN, limit=5)

    assert payload["discovery"]["intent"] == "discovery"
    assert [item["key"] for item in payload["discovery"]["filters"]] == ["power", "low_pb"]
    assert payload["stocks"][0]["symbol"] == "600900"
    assert set(payload["stocks"][0]["matched_tags"]) == {"power", "low_pb"}


def test_stock_discovery_strict_hides_weak_matches() -> None:
    svc = StockDiscoveryService(FakeStockService())
    payload = svc.discover("power + limit up", market=MarketCode.CN, limit=5, strict=True)

    assert payload["stocks"]
    assert payload["stocks"][0]["matched_tags"] == ["power"]


def test_user_decision_context_trader_is_compact() -> None:
    ctx = UserDecisionContextService().build_context(role="trader", user_id="u1", page="stock")

    assert ctx["role"] == "trader"
    assert ctx["response_density"] == "compact"
    assert ctx["dto_directives"]["include_raw_factors"] is False
    assert "signals" in ctx["dto_directives"]["primary_components"]


def test_user_decision_context_infers_researcher_from_profile() -> None:
    ctx = UserDecisionContextService().build_context(
        investment_profile={"style_tags": ["factor"], "risk_level": "aggressive"}
    )

    assert ctx["role"] == "researcher"
    assert ctx["dto_directives"]["include_raw_factors"] is True
    assert ctx["risk_context"]["risk_level"] == "aggressive"


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


def test_user_decision_context_api(app_client) -> None:
    resp = app_client.get("/api/v1/user/decision-context?role=researcher&page=stock")
    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert data["role"] == "researcher"
    assert data["dto_directives"]["include_raw_factors"] is True
