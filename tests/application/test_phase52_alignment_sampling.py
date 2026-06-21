"""Phase 52: alignment layer + K-line LTTB sampling."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
import werkzeug

from app.modules.strategy.services.analytics.headline_signal_enrichment_service import (
    HeadlineSignalEnrichmentService,
)
from app.domain.shared.bar_sampler import lttb_sample_ohlcv, resolve_sample_target
from app.domain.shared.market_time_aligner import DateAligner


def _bars(n: int) -> list[dict]:
    start = date(2024, 1, 1)
    return [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "open": float(i),
            "high": float(i) + 1,
            "low": float(i) - 0.5,
            "close": float(i) + 0.2,
            "volume": 1000 + i,
        }
        for i in range(n)
    ]


def test_resolve_sample_target_from_width() -> None:
    assert resolve_sample_target(None, 960) == 960
    assert resolve_sample_target(300, None) == 300
    assert resolve_sample_target(None, None) is None


def test_lttb_sample_reduces_points_preserving_endpoints() -> None:
    rows = _bars(200)
    out = lttb_sample_ohlcv(rows, 40)
    assert len(out) == 40
    assert out[0]["date"] == rows[0]["date"]
    assert out[-1]["date"] == rows[-1]["date"]


def test_lttb_sample_skips_when_under_target() -> None:
    rows = _bars(10)
    out = lttb_sample_ohlcv(rows, 50)
    assert out == rows


def test_date_aligner_cn_pre_open_maps_to_prior_session() -> None:
    slot = DateAligner.align_daily(
        "2024-01-16 09:15:00",
        market="CN",
        symbol="600519",
        is_trading_day=lambda ds: ds.startswith("2024-01-1"),
    )
    assert slot["date"] == "2024-01-15"
    assert slot["symbol"] == "sh600519"
    assert slot["granularity"] == "day"


def test_date_aligner_weekend_walks_back() -> None:
    slot = DateAligner.align_daily(
        "2024-01-14 15:00:00",
        market="CN",
        is_trading_day=lambda ds: ds == "2024-01-12",
    )
    assert slot["date"] == "2024-01-12"


def test_headline_enrichment_adds_market_time_slot() -> None:
    svc = HeadlineSignalEnrichmentService(cache=MagicMock(load=MagicMock(return_value={})))
    out = svc.enrich_headlines(
        [{"title": "test", "published_at": "2024-01-16 10:00:00", "summary": ""}],
        market="CN",
    )
    assert "market_time_slot" in out[0]
    assert out[0]["market_time_slot"]["date"]


@pytest.fixture
def app_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
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


def test_stock_history_api_sampling_meta(app_client) -> None:
    rows = _bars(120)
    with patch(
        "app.modules.market_data.services.stock_service.StockApplicationService.get_history",
        return_value=rows,
    ):
        resp = app_client.get(
            "/api/v1/stocks/CN/600519/history"
            "?start=2024-01-01&end=2024-04-30&max_points=30"
        )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["meta"]["sampled"] is True
    assert body["meta"]["original_point_count"] == 120
    assert body["meta"]["point_count"] == 30
    assert len(body["data"]) == 30
