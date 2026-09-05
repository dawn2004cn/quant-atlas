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
    save_cn_quote_book([{"code": "1", "name": "x"}], source="t")
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
    save_cn_quote_book([{"code": "1", "name": "x"}], source="t")
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
