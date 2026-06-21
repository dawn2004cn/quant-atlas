"""Phase 45: Decision Dashboard / UI-OPT workbench + headline signal cache."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import werkzeug

from app.modules.strategy.services.analytics.daily_workbench_service import DailyWorkbenchService
from app.modules.strategy.services.analytics.headline_signal_enrichment_service import (
    HeadlineSignalEnrichmentService,
)
from app.domain.enums import MarketCode
from app.infrastructure.cache.headline_signal_cache import HeadlineSignalCache


def test_headline_signal_rule_tag_bullish() -> None:
    svc = HeadlineSignalEnrichmentService()
    tag = svc.rule_tag({"title": "某股大涨突破，600519利好回购"})
    assert tag["signal_tag"] == "利好"
    assert tag["sentiment_score"] > 0
    assert "600519" in tag["affected_symbols"]


def test_headline_signal_cache_merge(tmp_path: Path) -> None:
    cache = HeadlineSignalCache(tmp_path / "signals")
    cache.merge("CN", {"k1": {"signal_tag": "利好", "sentiment_score": 0.5}})
    loaded = cache.load("CN")
    assert loaded["k1"]["signal_tag"] == "利好"
    cache.merge("CN", {"k2": {"signal_tag": "利空", "sentiment_score": -0.4}})
    merged = cache.load("CN")
    assert merged["k1"]["signal_tag"] == "利好"
    assert merged["k2"]["signal_tag"] == "利空"


def test_enrich_headlines_prefers_cache(tmp_path: Path) -> None:
    cache = HeadlineSignalCache(tmp_path / "signals")
    headline = {"title": "测试标题", "published_at": "2026-05-19 10:00"}
    key = HeadlineSignalEnrichmentService.headline_key(headline)
    cache.merge("CN", {key: {"signal_tag": "利空", "sentiment_score": -0.7, "affected_symbols": [], "confidence": 0.8}})
    svc = HeadlineSignalEnrichmentService(cache=cache)
    out = svc.enrich_headlines([headline], market="CN")
    assert out[0]["signal_tag"] == "利空"


def test_workbench_snapshot_decision_evidence_and_morning_call() -> None:
    market = MagicMock()
    market.get_panorama.return_value = {"up": 1200, "down": 800, "flat": 300}
    market.get_sentiment.return_value = {"score": 58, "level": "中性", "stats": {"gainers": 1, "losers": 1, "neutral": 1}}
    market.list_quotes.return_value = [{"code": "600519", "name": "贵州茅台", "price": 1700, "change_pct": 1.2}]
    watchlist = MagicMock()
    watchlist.list_symbols.return_value = ["600519"]
    svc = DailyWorkbenchService(market_service=market, watchlist_service=watchlist)
    snap = svc.build_snapshot(1, market=MarketCode.CN, focus_symbol="600519")
    assert snap["focus_context"]["symbol"] == "600519"
    assert snap["focus_context"]["symbol_label"] == "贵州茅台"
    assert "confidence" in snap["decision"]
    assert snap["decision"]["evidence"]
    assert len(snap["morning_call"]["slides"]) == 3
    assert snap["health_banner"]["level"] in ("ok", "warning", "critical")
    beat = snap["integration_digest"].get("timeseries_beat") or {}
    assert beat.get("available") is True
    assert "schedule_label" in beat


def test_workbench_integration_digest_includes_timeseries_beat() -> None:
    market = MagicMock()
    watchlist = MagicMock()
    svc = DailyWorkbenchService(market_service=market, watchlist_service=watchlist)
    digest = svc._integration_digest()
    beat = digest.get("timeseries_beat") or {}
    assert "available" in beat
    if beat.get("available"):
        assert "schedule_label" in beat


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


def test_daily_workbench_api_ui_opt_fields(app_client) -> None:
    resp = app_client.get("/api/v1/daily-workbench?market=CN&symbol=600519")
    assert resp.status_code == 200
    data = (resp.get_json() or {}).get("data") or {}
    assert "focus_context" in data
    assert "health_banner" in data
    assert "morning_call" in data
    assert data.get("decision", {}).get("evidence")
    beat = (data.get("integration_digest") or {}).get("timeseries_beat") or {}
    assert "available" in beat


def test_daily_workbench_page_200(app_client) -> None:
    resp = app_client.get("/")
    assert resp.status_code == 200
    assert b"wbFocusBar" in resp.data
    assert b"wbBeatSyncMini" in resp.data
    assert b"qa_user_center.js" in resp.data


def test_headline_signal_beat_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import patch

    with patch("app.celery_app.get_runtime") as mock_runtime, patch(
        "app.celery_app.get_runtime_int", side_effect=lambda key, default=0: 30 if "BEAT" in key else default
    ):
        mock_runtime.side_effect = lambda key, default="0": "1" if key == "HEADLINE_SIGNAL_CELERY_BEAT" else default
        from app.celery_app import _build_beat_schedule

        beat = _build_beat_schedule()
        assert "headline-signal-enrich-cn" in beat
