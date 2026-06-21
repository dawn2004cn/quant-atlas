"""Core MarketApplicationService tests — panorama and history paths."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.domain.enums import MarketCode
from app.modules.market_data.services.market_service import MarketApplicationService


@pytest.fixture
def market_svc():
    provider = SimpleNamespace(
        get_market_overview=lambda _m: {"market_status": "active", "sentiment_score": 0.1},
        get_market_rankings=lambda _m: {"gainers": [], "losers": [], "amounts": [], "turnovers": []},
        get_stock_history=lambda symbol, market, start, end: [
            {"date": start or "2024-01-01", "close": 1.0, "symbol": symbol},
        ],
    )
    return MarketApplicationService(
        market_provider=provider,
        industry_provider=SimpleNamespace(),
        stock_cache=None,
    )


def test_get_panorama_returns_dto_fields(market_svc):
    panorama = market_svc.get_panorama(MarketCode.CN)
    assert panorama.market_status == "active"
    assert panorama.sentiment_score == pytest.approx(0.1)


def test_get_history_bars_delegates_to_provider(market_svc):
    bars = market_svc.get_history_bars(
        "600519",
        MarketCode.CN,
        start_date="2024-01-01",
        end_date="2024-01-31",
        count=100,
    )
    assert len(bars) == 1
    assert bars[0]["symbol"] == "600519"


def test_get_history_returns_empty_when_provider_lacks_method(market_svc):
    market_svc._market_provider = SimpleNamespace()
    assert market_svc.get_history("600519", MarketCode.CN, start="2024-01-01", end="2024-01-02") == []
