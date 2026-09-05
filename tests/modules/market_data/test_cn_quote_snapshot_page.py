from __future__ import annotations

import time

from app.modules.market_data.services.cn_quote_snapshot import CnQuoteSnapshot


class _HangingMarketService:
    calls = 0

    def list_quotes(self, market, symbols=None):
        type(self).calls += 1
        time.sleep(30)
        return [{"code": "000002", "name": "hang", "price": 1, "change_pct": 0}]


def test_cn_quote_snapshot_query_page_filter_and_sort() -> None:
    snap = CnQuoteSnapshot(ttl_seconds=60)
    snap.load_rows([
        {"code": "600519", "name": "茅台", "price": 100, "change_pct": 10.0, "amount": 1e9},
        {"code": "000001", "name": "平安", "price": 10, "change_pct": -1.0, "amount": 2e8},
        {"code": "300750", "name": "宁德", "price": 50, "change_pct": 5.0, "amount": 5e8},
    ])
    page = snap.query_page(page=1, page_size=2, sort_key="change_pct", sort_order="desc", board_filter="all")
    assert page["total"] == 3
    assert len(page["items"]) == 2
    assert page["items"][0]["code"] == "600519"

    limit_up = snap.query_page(page=1, page_size=10, board_filter="limit_up")
    assert limit_up["total"] == 1
    assert limit_up["items"][0]["code"] == "600519"

    stats = page["stats"]
    assert stats["up"] == 2
    assert stats["down"] == 1


def test_cn_quote_snapshot_query_page_watchlist_codes() -> None:
    snap = CnQuoteSnapshot(ttl_seconds=60)
    snap.load_rows([
        {"code": "600519", "name": "茅台", "price": 100, "change_pct": 10.0},
        {"code": "000001", "name": "平安", "price": 10, "change_pct": -1.0},
        {"code": "300750", "name": "宁德", "price": 50, "change_pct": 5.0},
    ])
    page = snap.query_page(page=1, page_size=10, codes={"600519", "300750"})
    assert page["total"] == 2
    codes = {row["code"] for row in page["items"]}
    assert codes == {"600519", "300750"}


def test_cn_quote_snapshot_lookup_rows_ordered() -> None:
    snap = CnQuoteSnapshot(ttl_seconds=60)
    snap.load_rows([
        {"code": "600519", "name": "茅台", "price": 100, "change_pct": 10.0},
        {"code": "000001", "name": "平安", "price": 10, "change_pct": -1.0},
        {"code": "300750", "name": "宁德", "price": 50, "change_pct": 5.0},
    ])
    hits, missing = snap.lookup_rows(["300750", "999999", "600519", "300750"])
    assert [h["code"] for h in hits] == ["300750", "600519"]
    assert missing
    assert "999999" in missing[0] or missing[0].endswith("999999")


def test_ensure_fresh_returns_immediately_when_live_hangs() -> None:
    _HangingMarketService.calls = 0
    snap = CnQuoteSnapshot(market_service=_HangingMarketService(), ttl_seconds=15)
    started = time.monotonic()
    snap.ensure_fresh()
    assert time.monotonic() - started < 1.0
    page = snap.query_page()
    assert page["warming"] is True
    assert page["items"] == []
    assert page["total"] == 0


def test_ensure_fresh_keeps_stale_rows_when_live_hangs() -> None:
    snap = CnQuoteSnapshot(market_service=_HangingMarketService(), ttl_seconds=1)
    snap.load_rows([
        {"code": "600519", "name": "茅台", "price": 100, "change_pct": 1.0},
    ])
    time.sleep(1.05)
    started = time.monotonic()
    snap.ensure_fresh()
    assert time.monotonic() - started < 1.0
    page = snap.query_page()
    assert page["items"][0]["code"] == "600519"
    assert page["warming"] is True


class _LiveMarketService:
    def list_quotes(self, market, symbols=None, *, live: bool = True):
        if symbols:
            return [
                {"code": "".join(ch for ch in str(s) if ch.isdigit())[-6:].zfill(6), "name": "X", "price": 9, "change_pct": 1.2}
                for s in symbols
            ]
        if not live:
            return []
        return [{"code": "000001", "name": "平安", "price": 10, "change_pct": 1.5}]


def test_ensure_fresh_background_live_fills_empty_snapshot() -> None:
    snap = CnQuoteSnapshot(market_service=_LiveMarketService(), ttl_seconds=15)
    snap.ensure_fresh()
    deadline = time.time() + 2
    while time.time() < deadline and (snap.is_refreshing or not snap.unique_rows()):
        time.sleep(0.02)
    page = snap.query_page()
    assert page["total"] >= 1
    assert page["items"][0]["code"] == "000001"


def test_fill_missing_hydrates_symbol_lists_from_live() -> None:
    snap = CnQuoteSnapshot(market_service=_LiveMarketService(), ttl_seconds=15)
    snap.ensure_fresh()
    snap.fill_missing(["600519", "300750"], fetcher=lambda missing: _LiveMarketService().list_quotes(None, missing))
    page = snap.query_page(page=1, page_size=10, codes={"600519", "300750"})
    assert page["total"] == 2
    assert {row["code"] for row in page["items"]} == {"600519", "300750"}
