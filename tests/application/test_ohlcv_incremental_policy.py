from __future__ import annotations

from datetime import date

from app.modules.data.services.ohlcv_incremental_policy import (
    dedupe_bars_by_date,
    filter_rows_incremental,
    incremental_cursor_start,
    min_latest_date_str,
)


def test_incremental_cursor_overlap_reopens_window() -> None:
    end = date(2026, 5, 24)
    latest = date(2026, 5, 20)
    start = incremental_cursor_start(latest, end, lookback_days=30, overlap_days=3)
    assert start == date(2026, 5, 17)


def test_incremental_cursor_none_when_fresh() -> None:
    end = date(2026, 5, 24)
    latest = date(2026, 5, 30)
    assert incremental_cursor_start(latest, end, lookback_days=30, overlap_days=3) is None


def test_filter_rows_incremental_includes_overlap() -> None:
    rows = [
        {"date": "2026-05-18", "close": 1},
        {"date": "2026-05-19", "close": 2},
        {"date": "2026-05-20", "close": 3},
    ]
    out = filter_rows_incremental(rows, "2026-05-20", overlap_days=2)
    assert [r["date"] for r in out] == ["2026-05-18", "2026-05-19", "2026-05-20"]


def test_min_latest_date_str_picks_lagging_store() -> None:
    assert min_latest_date_str("2026-05-20", "2026-05-10") == "2026-05-10"


def test_dedupe_bars_by_date_last_wins() -> None:
    bars = [
        {"date": "2026-05-01", "close": 1},
        {"date": "2026-05-01", "close": 9},
    ]
    out = dedupe_bars_by_date(bars)
    assert len(out) == 1
    assert out[0]["close"] == 9
