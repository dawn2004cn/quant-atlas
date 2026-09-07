from __future__ import annotations

"""QuantStats-style performance tearsheet (stdlib + numpy/pandas only).

Reimplements the public formulas used by QuantStats / empyrical:
Omega, historical VaR/CVaR, tail ratio, Ulcer index, recovery factor.
"""

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd


def compute_tearsheet(
    returns: Sequence[float],
    *,
    threshold: float = 0.0,
    dates: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Compute a compact tearsheet from a periodic return series."""
    arr = np.asarray(list(returns), dtype=float)
    empty = {
        "omega_ratio": 0.0,
        "var_95": 0.0,
        "cvar_95": 0.0,
        "tail_ratio": 0.0,
        "ulcer_index": 0.0,
        "recovery_factor": 0.0,
        "monthly_returns": {},
    }
    if arr.size == 0 or not np.isfinite(arr).any():
        return empty

    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    gains = float(np.clip(arr - threshold, 0.0, None).sum())
    losses = float(np.clip(threshold - arr, 0.0, None).sum())
    omega = gains / losses if losses > 1e-12 else (float("inf") if gains > 0 else 0.0)

    var_95 = float(np.quantile(arr, 0.05))
    tail = arr[arr <= var_95]
    cvar_95 = float(tail.mean()) if tail.size else var_95

    p95 = float(np.percentile(arr, 95))
    p5 = float(np.percentile(arr, 5))
    tail_ratio = abs(p95) / abs(p5) if abs(p5) > 1e-12 else 0.0

    equity = np.concatenate(([1.0], np.cumprod(1.0 + arr)))
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak == 0, 1.0, peak)
    ulcer = float(np.sqrt(np.mean(np.square(dd))))
    max_dd = float(dd.min())
    total_return = float(equity[-1] - 1.0)
    recovery = total_return / abs(max_dd) if abs(max_dd) > 1e-12 else 0.0

    monthly: dict[str, float] = {}
    if dates is not None and len(list(dates)) == arr.size:
        series = pd.Series(arr, index=pd.to_datetime(list(dates), errors="coerce"))
        series = series[series.index.notna()]
        if not series.empty:
            grouped = series.groupby(series.index.to_period("M")).sum()
            monthly = {str(period): float(val) for period, val in grouped.items()}

    return {
        "omega_ratio": 0.0 if not np.isfinite(omega) else float(omega),
        "var_95": var_95,
        "cvar_95": cvar_95,
        "tail_ratio": float(tail_ratio),
        "ulcer_index": ulcer,
        "recovery_factor": float(recovery),
        "monthly_returns": monthly,
    }
