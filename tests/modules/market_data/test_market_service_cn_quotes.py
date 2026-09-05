"""CN full-market quote fallback when cache is partial."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.domain.enums import MarketCode
from app.modules.market_data.services import market_service as market_service_module
from app.modules.market_data.services.market_service import MarketApplicationService


def _partial_cache_rows(count: int) -> list[dict]:
    return [
        {
            "code": f"sh600{idx:03d}",
            "name": f"TEST{idx}",
            "price": 10.0,
            "change_pct": 1.0,
            "update_time": "2099-01-01 12:00:00",
        }
        for idx in range(count)
    ]


def test_list_cn_quotes_refreshes_when_cache_partial() -> None:
    cache = MagicMock()
    cache.get_all_stocks.return_value = _partial_cache_rows(249)

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

    live_rows = [{"code": f"{idx:06d}", "name": f"T{idx}", "price": 1.0, "change_pct": 0.1} for idx in range(4200)]
    with patch.object(svc, "_pull_akshare_cn_spot", return_value=[]):
        with patch.object(svc, "_pull_cn_via_tencent_batches", return_value=live_rows):
            quotes = svc.list_quotes(MarketCode.CN, None)

    assert len(quotes) >= market_service_module._CN_FULL_MARKET_MIN_ROWS


def test_list_cn_quotes_uses_cache_when_full_enough() -> None:
    cache = MagicMock()
    cache.get_all_stocks.return_value = _partial_cache_rows(1800)

    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=MagicMock(),
    ):
        svc = MarketApplicationService(
            market_provider=SimpleNamespace(),
            industry_provider=SimpleNamespace(),
            stock_cache=cache,
        )

    with patch.object(
        market_service_module.MarketApplicationService,
        "_pull_akshare_cn_spot",
    ) as live_mock:
        quotes = svc.list_quotes(MarketCode.CN, None)

    live_mock.assert_not_called()
    assert len(quotes) == 1800


def test_list_cn_quotes_live_false_returns_partial_cache() -> None:
    cache = MagicMock()
    cache.get_all_stocks.return_value = _partial_cache_rows(249)

    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=MagicMock(),
    ):
        svc = MarketApplicationService(
            market_provider=SimpleNamespace(),
            industry_provider=SimpleNamespace(),
            stock_cache=cache,
        )

    with patch.object(
        market_service_module.MarketApplicationService,
        "_pull_akshare_cn_spot",
    ) as live_mock:
        quotes = svc.list_quotes(MarketCode.CN, None, live=False)

    live_mock.assert_not_called()
    assert len(quotes) == 249
