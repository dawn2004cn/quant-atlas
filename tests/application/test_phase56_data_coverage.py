"""Phase 56: K-line data coverage indicator."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import werkzeug

from app.domain.enums import MarketCode
from app.domain.shared.data_coverage import assess_bar_coverage


def test_assess_bar_coverage_good() -> None:
    today = date.today()
    bars = [(today - timedelta(days=i)).isoformat() for i in range(25)]
    fn = lambda ds: date.fromisoformat(ds[:10]).weekday() < 5
    out = assess_bar_coverage(bars, lookback_days=20, as_of=today, is_trading_day=fn)
    assert out["level"] in ("good", "partial")
    assert out["coverage_pct"] >= 70


def test_assess_bar_coverage_poor_when_sparse() -> None:
    today = date.today()
    bars = [today.isoformat(), (today - timedelta(days=10)).isoformat()]
    fn = lambda ds: date.fromisoformat(ds[:10]).weekday() < 5
    out = assess_bar_coverage(bars, lookback_days=30, as_of=today, is_trading_day=fn)
    assert out["level"] == "poor"
    assert out["warning"]
    assert out["confidence_penalty"] > 0


def test_data_coverage_service_with_mock_history() -> None:
    from app.modules.market_data.services.data_coverage_service import DataCoverageService

    today = date.today()
    rows = [{"date": (today - timedelta(days=i)).isoformat(), "close": 10 + i} for i in range(28)]
    stock = MagicMock()
    stock.get_history.return_value = rows
    dto = DataCoverageService(stock).assess_symbol("600519", MarketCode.CN, lookback_days=20)
    assert dto.symbol == "600519"
    assert dto.expected_sessions > 0
    assert dto.level in ("good", "partial", "poor", "unknown")


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


def test_data_coverage_api(app_client) -> None:
    today = date.today()
    rows = [{"date": (today - timedelta(days=i)).isoformat(), "close": 100} for i in range(25)]
    with patch(
        "app.modules.market_data.services.stock_service.StockApplicationService.get_history",
        return_value=rows,
    ):
        resp = app_client.get("/api/v1/stocks/CN/600519/data-coverage?lookback_days=20")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "coverage_pct" in body["data"]
    assert body["data"]["level"]
