from __future__ import annotations

"""LTTB downsampling for OHLCV history rows."""

import math
from typing import Any


def resolve_sample_target(
    max_points: int | None,
    width: int | None,
    *,
    min_points: int = 80,
    max_cap: int = 2000,
) -> int | None:
    """Map explicit ``max_points`` or chart ``width`` (px) to a sampling target."""
    if max_points is not None and max_points > 0:
        return int(max(max_points, 3))
    if width is not None and width > 0:
        return int(max(min_points, min(max_cap, width)))
    return None


def _y_value(row: dict[str, Any]) -> float:
    for key in ("close", "Close", "adj_close", "Adj Close"):
        val = row.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return 0.0


def lttb_sample_ohlcv(
    rows: list[dict[str, Any]],
    target_points: int,
    *,
    y_key: str | None = None,
) -> list[dict[str, Any]]:
    """Largest-Triangle-Three-Buckets sampling; preserves first/last bars."""
    if target_points <= 0 or len(rows) <= target_points:
        return list(rows)
    if target_points < 3:
        return [rows[0], rows[-1]]

    data = list(rows)
    if y_key:
        ys = [float(row.get(y_key) or 0) for row in data]
    else:
        ys = [_y_value(row) for row in data]

    sampled_indices = _lttb_indices(ys, target_points)
    return [data[i] for i in sampled_indices]


def _lttb_indices(ys: list[float], threshold: int) -> list[int]:
    n = len(ys)
    if threshold >= n or threshold < 3:
        return list(range(n))

    sampled: list[int] = [0]
    bucket_size = (n - 2) / (threshold - 2)
    a = 0

    for i in range(threshold - 2):
        avg_range_start = int(math.floor((i + 1) * bucket_size)) + 1
        avg_range_end = int(math.floor((i + 2) * bucket_size)) + 1
        avg_range_end = min(avg_range_end, n)

        avg_x = 0.0
        avg_y = 0.0
        count = max(avg_range_end - avg_range_start, 0)
        if count > 0:
            for idx in range(avg_range_start, avg_range_end):
                avg_x += idx
                avg_y += ys[idx]
            avg_x /= count
            avg_y /= count

        range_start = int(math.floor(i * bucket_size)) + 1
        range_end = int(math.floor((i + 1) * bucket_size)) + 1
        range_end = min(range_end, n)

        max_area = -1.0
        next_a = range_start
        for idx in range(range_start, range_end):
            area = abs((a - avg_x) * (ys[idx] - ys[a]) - (a - idx) * (avg_y - ys[a])) * 0.5
            if area > max_area:
                max_area = area
                next_a = idx
        sampled.append(next_a)
        a = next_a

    sampled.append(n - 1)
    return sampled


__all__ = ["lttb_sample_ohlcv", "resolve_sample_target"]
