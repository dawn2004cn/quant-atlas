from __future__ import annotations

"""Alphalens / Qlib-style factor diagnostics: IC, Rank IC, ICIR, quantiles."""

from collections.abc import Sequence
from typing import Any

import numpy as np


def _is_panel(values: Sequence[Any]) -> bool:
    return bool(values) and isinstance(values[0], (list, tuple, np.ndarray))


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 3 or y.size != x.size:
        return 0.0
    rx = _ranks(x)
    ry = _ranks(y)
    n = float(x.size)
    d2 = float(np.sum((rx - ry) ** 2))
    denom = n * (n * n - 1.0)
    if denom <= 0:
        return 0.0
    return float(1.0 - (6.0 * d2) / denom)


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 3 or y.size != x.size:
        return 0.0
    if float(np.std(x)) < 1e-12 or float(np.std(y)) < 1e-12:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=float)
    ranks[order] = np.arange(1, values.size + 1, dtype=float)
    return ranks


def _quantile_means(factor: np.ndarray, fwd: np.ndarray, n_quantiles: int) -> list[float]:
    n = factor.size
    if n < n_quantiles:
        return [0.0] * n_quantiles
    order = np.argsort(factor, kind="mergesort")
    buckets = np.array_split(order, n_quantiles)
    means: list[float] = []
    for bucket in buckets:
        means.append(float(np.mean(fwd[bucket])) if bucket.size else 0.0)
    return means


def diagnose_factor(
    factor_values: Sequence[Any],
    forward_returns: Sequence[Any],
    *,
    n_quantiles: int = 5,
) -> dict[str, Any]:
    """Diagnose a factor vs aligned forward returns (series or date×name panel)."""
    empty = {
        "ic": 0.0,
        "rank_ic": 0.0,
        "icir": 0.0,
        "quantile_returns": [0.0] * n_quantiles,
        "long_short": 0.0,
        "sample_size": 0,
        "n_periods": 0,
    }
    if not factor_values or not forward_returns:
        return empty

    if _is_panel(factor_values) or _is_panel(forward_returns):
        if not _is_panel(factor_values) or not _is_panel(forward_returns):
            return empty
        if len(factor_values) != len(forward_returns):
            return empty
        ics: list[float] = []
        q_acc = np.zeros(n_quantiles, dtype=float)
        q_n = 0
        for f_row, r_row in zip(factor_values, forward_returns):
            f = np.asarray(f_row, dtype=float)
            r = np.asarray(r_row, dtype=float)
            if f.size != r.size or f.size < 3:
                continue
            ics.append(_spearman(f, r))
            q_acc += np.asarray(_quantile_means(f, r, n_quantiles), dtype=float)
            q_n += 1
        if not ics:
            return empty
        ic_arr = np.asarray(ics, dtype=float)
        rank_ic = float(ic_arr.mean())
        icir = float(ic_arr.mean() / max(float(ic_arr.std(ddof=1)), 1e-12)) if ic_arr.size > 1 else float(rank_ic)
        quantiles = (q_acc / q_n).tolist() if q_n else [0.0] * n_quantiles
        return {
            "ic": rank_ic,
            "rank_ic": rank_ic,
            "icir": icir,
            "quantile_returns": [float(q) for q in quantiles],
            "long_short": float(quantiles[-1] - quantiles[0]) if quantiles else 0.0,
            "sample_size": int(ic_arr.size * (np.asarray(factor_values[0], dtype=float).size)),
            "n_periods": int(ic_arr.size),
        }

    factor = np.asarray(factor_values, dtype=float)
    fwd = np.asarray(forward_returns, dtype=float)
    if factor.size != fwd.size or factor.size < 3:
        return empty
    quantiles = _quantile_means(factor, fwd, n_quantiles)
    rank_ic = _spearman(factor, fwd)
    return {
        "ic": _pearson(factor, fwd),
        "rank_ic": rank_ic,
        "icir": 0.0,
        "quantile_returns": quantiles,
        "long_short": float(quantiles[-1] - quantiles[0]) if quantiles else 0.0,
        "sample_size": int(factor.size),
        "n_periods": 1,
    }
