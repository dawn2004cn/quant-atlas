from __future__ import annotations
"""Numba-accelerated operators for alpha factor computation.

This enables rd-agent to generate complex, stateful factor logic
(e.g., recursive filtering) with high performance.

参考: qlib 动态算子扩展
"""



import numpy as np


try:
    from numba import jit, prange

    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    prange = range


if NUMBA_AVAILABLE:

    @jit(nopython=True, cache=True)
    def ts_rank_numba(arr: np.ndarray, window: int) -> np.ndarray:
        """Numba-accelerated time-series rank."""
        n = len(arr)
        result = np.empty(n, dtype=np.float64)

        for i in range(n):
            if i < window - 1:
                result[i] = 0.0
            else:
                sub = arr[i - window + 1 : i + 1]
                rank = 0
                for j in range(window):
                    if sub[j] <= arr[i]:
                        rank += 1
                result[i] = rank / window

        return result

    @jit(nopython=True, cache=True)
    def ts_argmax_numba(arr: np.ndarray, window: int) -> np.ndarray:
        """Numba-accelerated time-series argmax."""
        n = len(arr)
        result = np.empty(n, dtype=np.float64)

        for i in range(n):
            if i < window - 1:
                result[i] = 0.0
            else:
                max_val = arr[i - window + 1]
                max_idx = 0
                for j in range(1, window):
                    if arr[i - window + 1 + j] > max_val:
                        max_val = arr[i - window + 1 + j]
                        max_idx = j
                result[i] = max_idx

        return result

    @jit(nopython=True, cache=True)
    def ts_argmin_numba(arr: np.ndarray, window: int) -> np.ndarray:
        """Numba-accelerated time-series argmin."""
        n = len(arr)
        result = np.empty(n, dtype=np.float64)

        for i in range(n):
            if i < window - 1:
                result[i] = 0.0
            else:
                min_val = arr[i - window + 1]
                min_idx = 0
                for j in range(1, window):
                    if arr[i - window + 1 + j] < min_val:
                        min_val = arr[i - window + 1 + j]
                        min_idx = j
                result[i] = min_idx

        return result

    @jit(nopython=True, cache=True)
    def ts_zscore_numba(arr: np.ndarray, window: int) -> np.ndarray:
        """Numba-accelerated time-series z-score."""
        n = len(arr)
        result = np.empty(n, dtype=np.float64)

        for i in range(n):
            if i < window - 1:
                result[i] = 0.0
            else:
                sub = arr[i - window + 1 : i + 1]
                mean = np.mean(sub)
                std = np.std(sub)
                if std > 1e-10:
                    result[i] = (arr[i] - mean) / std
                else:
                    result[i] = 0.0

        return result

    @jit(nopython=True, cache=True)
    def decay_linear_numba(arr: np.ndarray, window: int) -> np.ndarray:
        """Numba-accelerated linear decay."""
        n = len(arr)
        result = np.empty(n, dtype=np.float64)

        weights = np.arange(1, window + 1, dtype=np.float64)
        weights = weights / np.sum(weights)

        for i in range(n):
            if i < window - 1:
                result[i] = 0.0
            else:
                sub = arr[i - window + 1 : i + 1]
                result[i] = np.sum(sub * weights[::-1])

        return result

    @jit(nopython=True, cache=True, parallel=True)
    def cross_sectional_rank_numba(
        values: np.ndarray, dates: np.ndarray
    ) -> np.ndarray:
        """Numba-accelerated cross-sectional rank (parallel)."""
        n = len(values)
        result = np.empty(n, dtype=np.float64)
        unique_dates = np.unique(dates)

        for d in prange(len(unique_dates)):
            date_val = unique_dates[d]
            mask = dates == date_val
            if np.sum(mask) > 0:
                date_values = values[mask]
                sorted_idx = np.argsort(date_values)
                ranks = np.empty_like(sorted_idx)
                ranks[sorted_idx] = np.arange(len(sorted_idx))

                for i in range(n):
                    if dates[i] == date_val:
                        idx = np.where(mask)[0][i]
                        result[idx] = ranks[np.where(np.arange(n)[mask] == idx)[0][0]] / len(date_values)

        return result

    @jit(nopython=True, cache=True)
    def signed_power_numba(arr: np.ndarray, power: float) -> np.ndarray:
        """Numba-accelerated signed power."""
        result = np.empty_like(arr)
        for i in range(len(arr)):
            if arr[i] >= 0:
                result[i] = arr[i] ** power
            else:
                result[i] = -(-arr[i]) ** power
        return result

    @jit(nopython=True, cache=True)
    def signed_log_numba(arr: np.ndarray) -> np.ndarray:
        """Numba-accelerated signed log."""
        result = np.empty_like(arr)
        for i in range(len(arr)):
            if arr[i] >= 0:
                result[i] = np.log1p(arr[i])
            else:
                result[i] = -np.log1p(-arr[i])
        return result

    NUMBA_OPERATORS = {
        "ts_rank": ts_rank_numba,
        "ts_argmax": ts_argmax_numba,
        "ts_argmin": ts_argmin_numba,
        "ts_zscore": ts_zscore_numba,
        "decay_linear": decay_linear_numba,
        "cross_sectional_rank": cross_sectional_rank_numba,
        "signed_power": signed_power_numba,
        "signed_log": signed_log_numba,
    }

else:

    def ts_rank_numba(arr: np.ndarray, window: int) -> np.ndarray:
        """Fallback: time-series rank."""
        from scipy import stats

        n = len(arr)
        result = np.full(n, 0.0)
        for i in range(window - 1, n):
            sub = arr[i - window + 1 : i + 1]
            result[i] = stats.rankdata(sub)[-1] / window
        return result

    def ts_argmax_numba(arr: np.ndarray, window: int) -> np.ndarray:
        """Fallback: time-series argmax."""
        n = len(arr)
        result = np.full(n, 0.0)
        for i in range(window - 1, n):
            sub = arr[i - window + 1 : i + 1]
            result[i] = np.argmax(sub)
        return result

    NUMBA_OPERATORS = {}


def get_operator(name: str):
    """Get Numba-accelerated operator by name."""
    return NUMBA_OPERATORS.get(name)


def apply_operator(name: str, arr: np.ndarray, **kwargs) -> np.ndarray:
    """Apply operator to array."""
    op = get_operator(name)
    if op is None:
        raise ValueError(f"Unknown operator: {name}")

    if name in ("ts_rank", "ts_argmax", "ts_argmin", "ts_zscore", "decay_linear"):
        return op(arr, kwargs.get("window", 20))
    if name in ("signed_power",):
        return op(arr, kwargs.get("power", 2.0))
    if name in ("signed_log",):
        return op(arr)

    return op(arr)


def format_numba_operators_prompt() -> str:
    """Generate Numba operators prompt for rd-agent."""
    lines = [
        "=== Numba-Accelerated Operators ===",
        "[可用算子]",
    ]

    for name in NUMBA_OPERATORS:
        lines.append(f"- {name} (Numba加速)")

    lines.append("")
    lines.append("[优势]")
    lines.append("- 比纯 Python 快 10-100x")
    lines.append("- 支持递归过滤等复杂逻辑")
    lines.append("- 零拷贝 (zero-copy)")

    return "\n".join(lines)
