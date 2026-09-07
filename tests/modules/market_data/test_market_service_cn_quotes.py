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


def test_list_quotes_tencent_skips_akshare() -> None:
    cache = MagicMock()
    cache.get_all_stocks.return_value = []
    cache.list_all_codes.return_value = []

    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=MagicMock(),
    ):
        svc = MarketApplicationService(
            market_provider=SimpleNamespace(),
            industry_provider=SimpleNamespace(),
            stock_cache=cache,
        )

    with patch.object(svc, "_pull_akshare_cn_spot") as ak_mock:
        with patch.object(
            svc,
            "_fetch_fresh_quotes_dict",
            return_value={"000001": {"code": "000001", "name": "平安", "price": 10, "change_pct": 1.2}},
        ):
            quotes = svc.list_quotes_tencent()

    ak_mock.assert_not_called()
    assert quotes
    code6 = "".join(ch for ch in str(quotes[0]["code"]) if ch.isdigit())[-6:]
    assert code6 == "000001"


def test_cn_universe_without_akshare_uses_seed() -> None:
    cache = MagicMock()
    cache.list_all_codes.return_value = ["600519"]
    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=MagicMock(),
    ):
        svc = MarketApplicationService(
            market_provider=SimpleNamespace(),
            industry_provider=SimpleNamespace(),
            stock_cache=cache,
        )
    codes = svc._fetch_cn_universe_codes(cache, allow_akshare=False)
    assert "600519" in codes
    assert "000001" in codes
    capped = svc._fetch_cn_universe_codes(cache, allow_akshare=False, max_symbols=3)
    assert capped[0] == "600519"
    assert len(capped) == 3


def test_build_panorama_uses_snapshot_when_provider_rankings_empty() -> None:
    cache = MagicMock()
    cache.get_all_stocks.return_value = []
    cache.list_all_codes.return_value = []
    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=MagicMock(),
    ):
        svc = MarketApplicationService(
            market_provider=SimpleNamespace(),
            industry_provider=SimpleNamespace(),
            stock_cache=cache,
        )
    from app.modules.market_data.services.cn_quote_snapshot import configure_cn_quote_snapshot

    snap = configure_cn_quote_snapshot(market_service=svc)
    snap.load_rows(
        [
            {"code": "600519", "name": "茅台", "price": 100, "change_pct": 3.2, "amount": 1e9},
            {"code": "000001", "name": "平安", "price": 10, "change_pct": -1.1, "amount": 2e8},
        ]
    )
    with patch(
        "app.modules.market_data.services.cn_quote_book.live_quote_pull_enabled",
        return_value=False,
    ):
        dto = svc._build_panorama(MarketCode.CN)
    assert dto.gainers
    assert dto.gainers[0].code in {"600519", "sz600519", "sh600519"} or str(dto.gainers[0].code).endswith("600519")
    assert dto.losers


def test_build_panorama_skips_provider_full_market_rankings() -> None:
    cache = MagicMock()
    cache.get_all_stocks.return_value = []
    cache.list_all_codes.return_value = []

    class _BoomProvider:
        def get_market_overview(self, _m):
            return {"market_status": "active", "sentiment_score": 0.2}

        def get_market_rankings(self, _m):
            return {
                "gainers": [{
                    "code": "999999",
                    "name": "缓存零价",
                    "price": 0,
                    "change_pct": 0,
                    "change_amount": 0,
                    "volume": 0,
                    "amount": 0,
                    "turnover": 0,
                }],
                "losers": [],
                "amounts": [],
                "turnovers": [],
            }

    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=MagicMock(),
    ):
        svc = MarketApplicationService(
            market_provider=_BoomProvider(),
            industry_provider=SimpleNamespace(),
            stock_cache=cache,
        )

    class _Live:
        def pull_cn_page_quotes(self, *, max_symbols: int = 80):
            return [
                {"code": "300112", "name": "万讯自控", "price": 10.55, "change_pct": 20.02, "amount": 3e8},
                {"code": "000001", "name": "平安", "price": 11.8, "change_pct": -1.1, "amount": 2e8},
            ]

        def list_quotes(self, *args, **kwargs):
            return []

    svc.pull_cn_page_quotes = _Live().pull_cn_page_quotes
    from app.modules.market_data.services.cn_quote_book import clear_cn_quote_book
    from app.modules.market_data.services.cn_quote_snapshot import configure_cn_quote_snapshot

    clear_cn_quote_book()
    configure_cn_quote_snapshot(market_service=svc)
    dto = svc._build_panorama(MarketCode.CN)
    assert dto.gainers
    code = str(dto.gainers[0].code)
    assert code.endswith("300112") or code == "300112"
    assert not code.endswith("999999")
