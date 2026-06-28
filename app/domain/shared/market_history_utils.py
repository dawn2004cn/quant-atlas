from __future__ import annotations

"""Pure helpers for OHLCV history rows."""

from typing import Any


def filter_sort_history(
    history: list[dict[str, Any]],
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    """Keep only [start, end] by trade date and sort ascending."""
    if not history:
        return []
    s0, e0 = start[:10], end[:10]
    out: list[dict[str, Any]] = []
    for h in history:
        d = h.get("date") or h.get("Date")
        if d is None:
            continue
        ds = str(d)[:10]
        if ds < s0 or ds > e0:
            continue
        out.append(h)
    out.sort(key=lambda x: str(x.get("date") or x.get("Date"))[:10])
    return out
