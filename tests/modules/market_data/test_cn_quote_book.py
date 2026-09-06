from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.modules.market_data.services.cn_quote_book import (
    clear_cn_quote_book,
    ensure_cn_quote_book,
    load_cn_quote_book,
    refresh_book_reason,
    save_cn_quote_book,
    should_refresh_book,
)
from app.modules.market_data.services.cn_quote_snapshot import CnQuoteSnapshot, hydrate_page_snapshot
from app.modules.market_data.services.market_service import MarketApplicationService


@pytest.fixture(autouse=True)
def _reset_cn_quote_book() -> None:
    clear_cn_quote_book()
    yield
    clear_cn_quote_book()


def test_save_and_load_cn_quote_book() -> None:
    save_cn_quote_book(
        [{"code": "600519", "name": "茅台", "price": 1600, "change_pct": 1.2}],
        source="test",
    )
    rows = load_cn_quote_book()
    assert rows
    assert rows[0]["code"] == "600519"


def test_load_cn_quote_book_reads_legacy_market_all_cache() -> None:
    fake = MagicMock()
    fake.get.side_effect = lambda key, default=None: (
        [{"code": "000001", "name": "平安", "price": 12.3, "change_pct": 0.4}]
        if key == "market_all_cache"
        else default
    )
    with patch("app.modules.market_data.services.cn_quote_book._cache", return_value=fake):
        rows = load_cn_quote_book()
    assert rows
    assert rows[0]["code"] == "000001"
    assert rows[0]["price"] == 12.3


def test_hydrate_zero_price_cache_uses_tencent_and_saves_book() -> None:
    class _ZeroThenLive:
        def list_quotes(self, *args, **kwargs):
            return [{"code": "000002", "name": "万科", "price": 0, "change_pct": 0}]

        def list_quotes_tencent(self, *args, **kwargs):
            return [{"code": "600519", "name": "茅台", "price": 1330.0, "change_pct": 2.4}]

        def pull_cn_page_quotes(self, *, max_symbols: int = 80):
            return self.list_quotes_tencent(max_symbols=max_symbols)

    snap = CnQuoteSnapshot(ttl_seconds=15)
    hydrate_page_snapshot(snap, _ZeroThenLive())
    page = snap.query_page()
    assert page["items"][0]["code"] == "600519"
    assert page["items"][0]["price"] == 1330.0
    stored = load_cn_quote_book()
    assert stored and stored[0]["price"] == 1330.0


def test_hydrate_prefers_redis_book_over_tencent() -> None:
    clear_cn_quote_book()
    save_cn_quote_book(
        [{"code": "000001", "name": "平安", "price": 12, "change_pct": 0.5}],
        source="redis",
    )

    class _Boom:
        def list_quotes(self, *args, **kwargs):
            return []

        def list_quotes_tencent(self, *args, **kwargs):
            raise AssertionError("page path must read Redis book, not live Tencent")

    snap = CnQuoteSnapshot(ttl_seconds=15)
    hydrate_page_snapshot(snap, _Boom())
    page = snap.query_page()
    assert page["items"][0]["code"] == "000001"


def test_hydrate_redis_book_overrides_warm_snapshot_and_stock_cache() -> None:
    save_cn_quote_book(
        [{"code": "600519", "name": "茅台", "price": 1700, "change_pct": 2.0}],
        source="redis",
    )

    class _CacheService:
        def list_quotes(self, *args, **kwargs):
            return [{"code": "000002", "name": "万科", "price": 8, "change_pct": 0}]

        def list_quotes_tencent(self, *args, **kwargs):
            raise AssertionError("must not hit Tencent when Redis book exists")

    snap = CnQuoteSnapshot(ttl_seconds=15)
    snap.load_rows([{"code": "000001", "name": "旧快照", "price": 1, "change_pct": 0}])
    hydrate_page_snapshot(snap, _CacheService())
    page = snap.query_page()
    assert page["items"][0]["code"] == "600519"
    assert page["total"] == 1


def test_refresh_book_reason_treats_zero_price_book_as_empty() -> None:
    save_cn_quote_book(
        [{"code": "000002", "name": "万科", "price": 0, "change_pct": 0}],
        source="seed",
    )
    with patch(
        "app.modules.market_data.services.cn_quote_book._is_cn_session",
        return_value=False,
    ):
        assert should_refresh_book(force=False) is True
        assert refresh_book_reason() == "empty"


def test_get_quotes_treats_zero_price_cache_as_miss() -> None:
    quote_cache = MagicMock()
    quote_cache.get_quotes.return_value = {
        "sh600519": {"code": "600519", "name": "茅台", "price": 0.0},
    }
    provider = SimpleNamespace(
        get_realtime_quotes=lambda codes, market=None: [
            {"code": "600519", "name": "茅台", "price": 1330.0, "change_pct": 1.2}
        ]
    )
    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=quote_cache,
    ):
        svc = MarketApplicationService(
            market_provider=provider,
            industry_provider=SimpleNamespace(),
            stock_cache=MagicMock(),
        )
    result = svc.get_quotes(["sh600519"])
    priced = next(iter(result.values()))
    assert float(priced["price"] if isinstance(priced, dict) else priced.get("price")) == 1330.0


def test_pull_cn_page_quotes_bypasses_zero_price_quote_cache() -> None:
    from app.domain.enums import MarketCode
    from app.domain.shared.value_objects import StockQuote

    quote_cache = MagicMock()
    quote_cache.get_quotes.return_value = {
        "sh600519": {"code": "600519", "name": "茅台", "price": 0.0},
        "600519": {"code": "600519", "name": "茅台", "price": 0.0},
    }
    live = StockQuote(
        code="600519",
        name="贵州茅台",
        market=MarketCode.CN,
        price=1330.0,
        change_pct=2.4,
    )
    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=quote_cache,
    ):
        svc = MarketApplicationService(
            market_provider=None,
            industry_provider=SimpleNamespace(),
            stock_cache=MagicMock(),
        )
    with patch.object(svc, "get_quotes", side_effect=AssertionError("must not use quote cache")):
        with patch(
            "app.infrastructure.adapters.tencent_quote_gateway.TencentQuoteGateway.fetch_quotes_text",
            return_value="v_sh600519=\"ok\"",
        ):
            with patch(
                "app.infrastructure.mappers.tencent_quote_mapper.TencentQuoteMapper.parse_payload",
                return_value=[live],
            ):
                rows = svc.pull_cn_page_quotes(max_symbols=1)
    assert rows
    assert all(float(r.get("price") or 0) > 0 for r in rows)
    assert any(str(r.get("code6") or r.get("code") or "").endswith("600519") for r in rows)


def test_pull_cn_page_quotes_keeps_priced_rows_only() -> None:
    cache = MagicMock()
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
        svc,
        "_fetch_tencent_live_quotes",
        return_value=[
            {"code": "sh600519", "code6": "600519", "name": "茅台", "price": 1330, "change_pct": 2.4},
        ],
    ):
        rows = svc.pull_cn_page_quotes(max_symbols=8)
    assert any(str(r.get("code6") or r.get("code") or "").endswith("600519") and float(r["price"]) == 1330 for r in rows)
    assert all(float(r.get("price") or 0) > 0 for r in rows)


def test_refresh_cn_quote_book_writes_store() -> None:
    cache = MagicMock()
    cache.get_all_stocks.return_value = []
    cache.list_all_codes.return_value = []
    live = [{"code": "300750", "name": "宁德", "price": 200, "change_pct": 2.0}]
    with patch(
        "app.modules.market_data.services.market_service.get_quote_cache_port",
        return_value=MagicMock(),
    ):
        svc = MarketApplicationService(
            market_provider=SimpleNamespace(),
            industry_provider=SimpleNamespace(),
            stock_cache=cache,
        )
    with patch.object(svc, "_pull_cn_via_tencent_batches", return_value=live):
        with patch.object(svc, "_pull_akshare_cn_spot") as ak:
            rows = svc.refresh_cn_quote_book(allow_akshare=False)
    ak.assert_not_called()
    assert rows[0]["code"] == "300750"
    stored = load_cn_quote_book()
    assert any(r.get("code") == "300750" for r in stored)


def test_should_refresh_when_book_empty() -> None:
    clear_cn_quote_book()
    assert should_refresh_book(force=False) is True
    assert should_refresh_book(force=True) is True


def test_should_refresh_in_session_when_book_exists() -> None:
    save_cn_quote_book([{"code": "1", "name": "x", "price": 10.0}], source="t")
    with patch(
        "app.modules.market_data.services.cn_quote_book._is_cn_session",
        return_value=True,
    ):
        assert should_refresh_book(force=False) is True
        assert refresh_book_reason() == "session"


def test_should_refresh_when_empty_outside_session() -> None:
    with patch(
        "app.modules.market_data.services.cn_quote_book._is_cn_session",
        return_value=False,
    ):
        assert should_refresh_book(force=False) is True
        assert refresh_book_reason() == "empty"


def test_should_skip_when_book_exists_outside_session() -> None:
    save_cn_quote_book([{"code": "1", "name": "x", "price": 10.0}], source="t")
    with patch(
        "app.modules.market_data.services.cn_quote_book._is_cn_session",
        return_value=False,
    ):
        assert should_refresh_book(force=False) is False
        assert refresh_book_reason() is None


def test_ensure_cn_quote_book_pulls_once_when_empty_off_hours() -> None:
    pulled: list[bool] = []

    class _Svc:
        def refresh_cn_quote_book(self, *, allow_akshare: bool = False):
            pulled.append(allow_akshare)
            save_cn_quote_book(
                [{"code": "600519", "name": "茅台", "price": 1600, "change_pct": 0.1}],
                source="offhours",
            )
            return load_cn_quote_book()

    with patch(
        "app.modules.market_data.services.cn_quote_book._is_cn_session",
        return_value=False,
    ):
        assert ensure_cn_quote_book(_Svc()) == "scheduled"
        deadline = time.monotonic() + 2.0
        while not pulled and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pulled == [False]
        assert load_cn_quote_book()
        assert ensure_cn_quote_book(_Svc()) == "present"


def test_ensure_cn_quote_book_only_attempts_once_while_empty() -> None:
    class _Empty:
        calls = 0

        def refresh_cn_quote_book(self, *, allow_akshare: bool = False):
            type(self).calls += 1
            return []

    _Empty.calls = 0
    first = ensure_cn_quote_book(_Empty())
    assert first == "scheduled"
    deadline = time.monotonic() + 2.0
    while _Empty.calls == 0 and time.monotonic() < deadline:
        time.sleep(0.05)
    second = ensure_cn_quote_book(_Empty())
    assert second == "attempted"
    time.sleep(0.1)
    assert _Empty.calls == 1


def test_ensure_disabled_when_live_pull_off() -> None:
    class _Boom:
        def refresh_cn_quote_book(self, *, allow_akshare: bool = False):
            raise AssertionError("must not pull when CN_QUOTE_LIVE_PULL=0")

    with patch(
        "app.modules.market_data.services.cn_quote_book.live_quote_pull_enabled",
        return_value=False,
    ):
        assert ensure_cn_quote_book(_Boom()) == "disabled"
