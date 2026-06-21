"""Market sentiment breadth tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.domain.enums import MarketCode
from app.modules.market_data.services.market_service import MarketApplicationService


@pytest.fixture
def market_svc_with_cache():
    cache = MagicMock()
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


def test_get_sentiment_refreshes_when_cache_sample_too_small(market_svc_with_cache):
    svc, cache = market_svc_with_cache
    cache.get_latest_sentiment.return_value = {
        "up_count": 56,
        "down_count": 44,
        "flat_count": 1,
        "total_count": 101,
        "update_time": "2026-06-16T02:00:00+00:00",
    }
    frame = pd.DataFrame(
        {
            "涨跌幅": [1.0] * 2600 + [-1.0] * 2400 + [0.0] * 100,
        }
    )
    with patch("akshare.stock_zh_a_spot_em", return_value=frame):
        payload = svc.get_sentiment(MarketCode.CN)

    assert payload["stats"]["total"] == 5100
    assert payload["stats"]["gainers"] == 2600
    assert payload["stats"]["losers"] == 2400
    assert payload["stats"]["neutral"] == 100
    assert "全市场实时" in payload["description"]
    cache.save_sentiment.assert_called_once_with("CN", 2600, 2400, 100)


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
