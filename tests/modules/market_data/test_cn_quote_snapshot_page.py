from __future__ import annotations

from app.modules.market_data.services.cn_quote_snapshot import CnQuoteSnapshot


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
