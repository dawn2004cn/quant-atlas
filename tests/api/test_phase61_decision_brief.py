"""Phase 61: stock decision brief semantic components."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import werkzeug

from app.modules.system.services.ui.decision_brief_service import DecisionBriefService


def test_decision_brief_builds_semantic_components() -> None:
    detail = {
        "profile": {
            "industry": "consumer",
            "realtime": {
                "name": "Demo Stock",
                "price": 10.5,
                "change_pct": 1.2,
                "volume": 1000,
            },
        },
        "quote_fact": {"close_fact": "10.50", "trace_ref": {"anchor": "quote"}},
        "data_coverage": {"level": "good", "coverage_pct": 95, "warning": ""},
    }
    timeline = {
        "summary": {"count": 2, "by_type": {"news": 1, "price_move": 1}, "has_evidence": True},
        "markers": [
            {"date": "2026-05-20", "type": "news", "title": "headline"},
            {"date": "2026-05-21", "type": "price_move", "title": "move"},
        ],
    }

    brief = DecisionBriefService().build_brief(
        symbol="600519",
        market="CN",
        stock_detail=detail,
        timeline=timeline,
        decision_context={"role": "trader", "response_density": "compact", "dto_directives": {}},
    )

    component_types = [item["type"] for item in brief["components"]]
    assert component_types == ["quote_strip", "risk_banner", "evidence_timeline", "action_bar"]
    assert brief["header"]["name"] == "Demo Stock"
    assert brief["warnings"] == []


def test_decision_brief_warns_on_partial_data() -> None:
    brief = DecisionBriefService().build_brief(
        symbol="600519",
        market="CN",
        stock_detail={
            "profile": {"realtime": {}},
            "data_coverage": {"level": "poor", "warning": "missing bars"},
        },
        timeline={"markers": [], "data_gaps": ["news: timeout"]},
        decision_context={"role": "researcher", "response_density": "deep", "dto_directives": {}},
    )

    codes = {item["code"] for item in brief["warnings"]}
    assert {"data_coverage_low", "timeline_partial"} <= codes
    actions = brief["components"][-1]["payload"]["items"]
    assert any(item["id"] == "open_reports" for item in actions)


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


def test_decision_brief_api(app_client) -> None:
    detail = {
        "symbol": "600519",
        "profile": {
            "realtime": {
                "name": "Demo Stock",
                "price": 10.5,
                "change_pct": 1.2,
                "volume": 1000,
            }
        },
        "indicators": {"ma20": 10.0},
    }
    history = [{"date": "2026-05-20", "close": 10.5, "volume": 1000, "amount": 1000}]
    with patch(
        "app.modules.market_data.services.stock_service.StockApplicationService.get_stock_detail",
        return_value=detail,
    ), patch(
        "app.modules.market_data.services.stock_service.StockApplicationService.get_history",
        return_value=history,
    ):
        resp = app_client.get("/api/v1/stocks/CN/600519/decision-brief?role=trader")

    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert data["role"] == "trader"
    assert data["components"]
    assert data["decision_context"]["response_density"] == "compact"
