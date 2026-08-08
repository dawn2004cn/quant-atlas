from __future__ import annotations

from app.domain.shared.market_history_utils import clamp_history_date_range


def test_clamp_history_date_range_caps_wide_window() -> None:
    start, end = clamp_history_date_range(
        "2018-01-01",
        "2026-07-28",
        max_points=400,
    )
    assert end == "2026-07-28"
    assert start > "2018-01-01"
    assert (start >= "2024-01-01") or (start >= "2023-06-01")


def test_clamp_history_date_range_keeps_narrow_window() -> None:
    start, end = clamp_history_date_range(
        "2026-01-01",
        "2026-07-28",
        max_points=400,
    )
    assert start == "2026-01-01"
    assert end == "2026-07-28"
