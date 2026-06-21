"""Cash dividend helpers for unadjusted-price backtests."""

from __future__ import annotations

from typing import Any

import pandas as pd

_DIVIDEND_COLUMNS = ("Dividend", "dividend", "cash_div", "Cash_Dividend")


def dividend_per_share(bar: Any) -> float:
    """Return per-share cash dividend on a bar (0 if none)."""
    for col in _DIVIDEND_COLUMNS:
        if col not in bar:
            continue
        value = bar[col]
        if value is None or (isinstance(value, float) and pd.isna(value)):
            continue
        try:
            amount = float(value)
        except (TypeError, ValueError):
            continue
        if amount > 0:
            return amount
    return 0.0


def dividend_cash_for_bar(bar: Any, shares: float) -> float:
    """Cash dividend credited to a position on ex-date."""
    if shares <= 0:
        return 0.0
    return shares * dividend_per_share(bar)
