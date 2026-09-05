"""Market sentiment breadth tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.domain.enums import MarketCode
from app.modules.market_data.services.market_service import MarketApplicationService


@pytest.fixture
def market_svc_with_cache():
    cache = MagicMock()
    cache.get_all_stocks.return_value = []
    cache.list_all_codes.return_value = []
    provider = SimpleNamespace()
    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=MagicMock(),
    ):
        svc = MarketApplicationService(
            market_provider=provider,
            industry_provider=SimpleNamespace(),
            stock_cache=cache,
        )
    return svc, cache


def test_get_sentiment_skips_akshare_when_cache_sample_too_small(market_svc_with_cache):
    svc, cache = market_svc_with_cache
    cache.get_latest_sentiment.return_value = {
        "up_count": 56,
        "down_count": 44,
        "flat_count": 1,
        "total_count": 101,
        "update_time": "2026-06-16T02:00:00+00:00",
    }
    with patch.object(svc, "_pull_akshare_cn_spot") as ak_spot:
        payload = svc.get_sentiment(MarketCode.CN)

    ak_spot.assert_not_called()
    assert payload["stats"]["total"] >= 0
    assert "stock_zh_a_spot_em" not in str(payload)


def test_get_sentiment_uses_fresh_full_cache(market_svc_with_cache):
    svc, cache = market_svc_with_cache
    cache.get_latest_sentiment.return_value = {
        "up_count": 2800,
        "down_count": 2100,
        "flat_count": 200,
        "total_count": 5100,
        "update_time": "2099-01-01T00:00:00+00:00",
    }
    payload = svc.get_sentiment(MarketCode.CN)
    assert payload["stats"]["total"] == 5100
    assert payload["description"].startswith("当前市场")
