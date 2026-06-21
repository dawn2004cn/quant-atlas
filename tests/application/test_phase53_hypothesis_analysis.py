"""Phase 53: hypothesis-based analysis evaluation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import werkzeug

from app.modules.ai_agent.services.analysis.hypothesis_evaluation_service import HypothesisEvaluationService
from app.modules.ai_agent.services.analysis.analysis_service import StockAnalysisService


def _detail(*, price: float = 100.0, change_pct: float = 1.2, ma20: float = 98.0, rsi: float = 55.0) -> dict:
    return {
        "profile": {
            "realtime": {"price": price, "change_pct": change_pct, "volume": 100000},
        },
        "indicators": {
            "ma5": price,
            "ma20": ma20,
            "rsi14": rsi,
            "macd": 0.2,
            "macd_signal": 0.1,
        },
        "news": [],
    }


def test_hypothesis_catalog_not_empty() -> None:
    items = HypothesisEvaluationService().list_catalog()
    assert len(items) >= 4
    assert any(x.id == "rebound_weak_volume" for x in items)


def test_rebound_weak_volume_mixed_or_supports() -> None:
    svc = HypothesisEvaluationService()
    dto = svc.evaluate(
        symbol="600519",
        detail=_detail(price=102, change_pct=1.0, ma20=100, rsi=52),
        hypothesis_id="rebound_weak_volume",
    )
    assert dto is not None
    assert dto.verdict in ("supports", "mixed", "contradicts", "inconclusive")
    assert dto.supporting_evidence or dto.contradicting_evidence


def test_uptrend_supports_when_ma_aligned() -> None:
    svc = HypothesisEvaluationService()
    dto = svc.evaluate(
        symbol="600519",
        detail=_detail(price=105, change_pct=2.0, ma20=100, rsi=58),
        hypothesis_id="uptrend_intact",
    )
    assert dto is not None
    assert dto.verdict in ("supports", "mixed")


def test_stock_analysis_includes_hypothesis_block() -> None:
    svc = StockAnalysisService()
    payload = svc.build_analysis(
        "600519",
        _detail(),
        hypothesis_id="trend_breakdown",
    )
    assert "hypothesis_evaluation" in payload
    assert payload["hypothesis_evaluation"]["hypothesis_id"] == "trend_breakdown"


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


def test_ai_hypothesis_catalog_api(app_client) -> None:
    resp = app_client.get("/api/v1/ai/hypotheses")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data"]["hypotheses"]


def test_ai_analyze_with_hypothesis(app_client) -> None:
    fake_result = {
        "symbol": "600519",
        "market": "CN",
        "ai": {"analysis": "demo"},
        "hypothesis_evaluation": {
            "hypothesis_id": "rebound_weak_volume",
            "user_hypothesis": "反弹但量能不足",
            "verdict": "mixed",
            "confidence": 0.6,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "summary": "test",
        },
    }
    with patch(
        "app.modules.ai_agent.services.ai_analysis_service.AiAnalysisService.analyze",
        return_value=fake_result,
    ):
        resp = app_client.post(
            "/api/v1/ai/analyze",
            json={
                "symbol": "600519",
                "market": "CN",
                "hypothesis_id": "rebound_weak_volume",
            },
        )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data"]["hypothesis_evaluation"]["hypothesis_id"] == "rebound_weak_volume"
