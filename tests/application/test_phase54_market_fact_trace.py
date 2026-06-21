"""Phase 54: factual price labels + conclusion trace refs."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import werkzeug

from app.domain.shared.market_fact import (
    enrich_history_with_facts,
    enrich_quote_with_facts,
    format_price_fact,
    ma_deviation_pct,
)


def test_ma_deviation_pct() -> None:
    assert ma_deviation_pct(102.0, 100.0) == 2.0
    assert ma_deviation_pct(0, 100) is None


def test_format_price_fact_with_ma20() -> None:
    fact = format_price_fact(10.2, 10.45)
    assert "MA20" in fact["close_fact"]
    assert fact["ma20_deviation_pct"] is not None


def test_enrich_history_adds_close_fact_and_trace() -> None:
    start = date(2024, 1, 1)
    rows = [
        {"date": (start + timedelta(days=i)).isoformat(), "close": 100.0 + i}
        for i in range(25)
    ]
    out = enrich_history_with_facts(rows)
    assert out[-1].get("close_fact")
    assert out[-1].get("trace_ref", {}).get("section_id") == "stockChart"


def test_enrich_quote_with_facts() -> None:
    fact = enrich_quote_with_facts(
        {"price": 50.0},
        {"ma20": 48.0, "ma5": 49.0},
        symbol="600519",
        market="CN",
    )
    assert fact["close_fact"]
    assert fact["trace_ref"]["href"].startswith("/stock/600519")


def test_hypothesis_evidence_has_trace_ref() -> None:
    from app.modules.ai_agent.services.analysis.hypothesis_evaluation_service import HypothesisEvaluationService

    svc = HypothesisEvaluationService()
    dto = svc.evaluate(
        symbol="600519",
        market="CN",
        detail={
            "profile": {"realtime": {"price": 102, "change_pct": 1.0}},
            "indicators": {"ma20": 100, "ma5": 101, "rsi14": 52, "macd": 0.1, "macd_signal": 0.0},
        },
        hypothesis_id="rebound_weak_volume",
    )
    assert dto is not None
    items = dto.supporting_evidence + dto.contradicting_evidence
    assert items
    assert items[0].trace_ref
    assert items[0].trace_ref.get("href")


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


def test_stock_history_includes_close_fact(app_client) -> None:
    start = date(2024, 1, 1)
    rows = [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "open": 100 + i,
            "high": 101 + i,
            "low": 99 + i,
            "close": 100 + i,
            "volume": 1000,
        }
        for i in range(30)
    ]
    with patch(
        "app.modules.market_data.services.stock_service.StockApplicationService.get_history",
        return_value=rows,
    ):
        resp = app_client.get(
            "/api/v1/stocks/CN/600519/history?start=2024-01-01&end=2024-02-15"
        )
    assert resp.status_code == 200
    body = resp.get_json()
    last = body["data"][-1]
    assert last.get("close_fact")
    assert last.get("trace_ref")
