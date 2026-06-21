"""Alpha factor expression engine — Polars-based factor computation DSL.

Inspired by vnpy.alpha.dataset, extracted and adapted for quant-atlas.

Usage:
    from app.core.alpha import DataProxy, calculate_expression, register_ts_operator

    # Expression-based factor
    df = load_bars("600519")
    result = calculate_expression(df, "ts_sum(close, 5) / ts_mean(close, 20)")

    # Programmatic factor using DataProxy operators
    close = DataProxy(df, "close")
    factor = (close - close.ts_mean(20)) / close.ts_std(20)
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import numpy as np
import polars as pl
from scipy import stats as scipy_stats

from app.core.logger import get_logger

logger = get_logger(__name__)


class DataProxy:
    """Feature data proxy with operator overloading and chaining.

    Wraps a Polars DataFrame with columns ``["datetime", "vt_symbol", "data"]``
    and delegates arithmetic, comparison, and time-series operations via
    operator overloading.  The ``data`` column is the carrier of the computed
    feature.

    Args:
        df: Polars DataFrame with at minimum ``["datetime", "vt_symbol", <name>]``.
        name: Column name to use as ``data``. If omitted, the last non-index column is used.
    """

    def __init__(self, df: pl.DataFrame, name: str | None = None) -> None:
        if name is None:
            candidates = [c for c in df.columns if c not in ("datetime", "vt_symbol")]
            name = candidates[-1] if candidates else df.columns[-1]
        self._name: str = name
        self.df: pl.DataFrame = df.rename({name: "data"}) if name in df.columns else df

    def result(self, s: pl.Series) -> DataProxy:
        result = self.df[["datetime", "vt_symbol"]].with_columns(other=s)
        return DataProxy(result, "other")

    # ── Arithmetic ─────────────────────────────────────────────────

    def __add__(self, other: Any) -> DataProxy:
        return self._arith(other, lambda a, b: a + b)

    def __sub__(self, other: Any) -> DataProxy:
        return self._arith(other, lambda a, b: a - b)

    def __mul__(self, other: Any) -> DataProxy:
        return self._arith(other, lambda a, b: a * b)

    def __truediv__(self, other: Any) -> DataProxy:
        return self._arith(other, lambda a, b: a / b)

    def __rmul__(self, other: Any) -> DataProxy:
        return self._arith(other, lambda a, b: a * b)

    def __abs__(self) -> DataProxy:
        return self.result(self.df["data"].abs())

    def __neg__(self) -> DataProxy:
        return self.result(-self.df["data"])

    def __pow__(self, power: float) -> DataProxy:
        return DataProxy(self.df.with_columns(
            pl.when(pl.col("data") > 0).then(pl.col("data").pow(power))
            .when(pl.col("data") < 0).then(-pl.col("data").abs().pow(power))
            .otherwise(0).alias("data")
        ))

    # ── Comparison (return 0/1 Int32) ───────────────────────────────

    def __gt__(self, other: Any) -> DataProxy:
        return self._cmp(other, lambda a, b: a > b)

    def __ge__(self, other: Any) -> DataProxy:
        return self._cmp(other, lambda a, b: a >= b)

    def __lt__(self, other: Any) -> DataProxy:
        return self._cmp(other, lambda a, b: a < b)

    def __le__(self, other: Any) -> DataProxy:
        return self._cmp(other, lambda a, b: a <= b)

    def __eq__(self, other: Any) -> DataProxy:  # type: ignore[override]
        return self._cmp(other, lambda a, b: a == b)

    def _arith(self, other: Any, op: Any) -> DataProxy:
        if isinstance(other, DataProxy):
            merged = self.df.join(other.df, on=["datetime", "vt_symbol"], suffixes=("", "_r"))
            return DataProxy(merged.with_columns(op(pl.col("data"), pl.col("data_r")).alias("data")))
        return self.result(op(self.df["data"], other))

    def _cmp(self, other: Any, op: Any) -> DataProxy:
        if isinstance(other, DataProxy):
            merged = self.df.join(other.df, on=["datetime", "vt_symbol"], suffixes=("", "_r"))
            return DataProxy(merged.with_columns(op(pl.col("data"), pl.col("data_r")).cast(pl.Int32).alias("data")))
        return self.result(op(self.df["data"], other).cast(pl.Int32))

    # ── Time-series operators (return new DataProxy) ────────────────

    def ts_delay(self, window: int) -> DataProxy:
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").shift(window).over("vt_symbol").alias("data")
        ))

    def ts_min(self, window: int) -> DataProxy:
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_min(window, min_samples=1).over("vt_symbol").alias("data")
        ))

    def ts_max(self, window: int) -> DataProxy:
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_max(window, min_samples=1).over("vt_symbol").alias("data")
        ))

    def ts_sum(self, window: int) -> DataProxy:
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_sum(window).over("vt_symbol").alias("data")
        ))

    def ts_mean(self, window: int) -> DataProxy:
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_mean(window).over("vt_symbol").alias("data")
        ))

    def ts_std(self, window: int) -> DataProxy:
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_std(window).over("vt_symbol").alias("data")
        ))

    def ts_rank(self, window: int) -> DataProxy:
        def _pct_rank(s: pl.Series) -> float:
            return float(scipy_stats.percentileofscore(s, s[-1]) / 100)
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_map(_pct_rank, window).over("vt_symbol").alias("data")
        ))

    def ts_corr(self, other: DataProxy, window: int) -> DataProxy:
        merged = self.df.join(other.df, on=["datetime", "vt_symbol"], suffixes=("", "_r"))
        corr = merged.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_corr(pl.col("data_r"), window_size=window).over("vt_symbol").alias("data")
        )
        return DataProxy(corr)

    def ts_cov(self, other: DataProxy, window: int) -> DataProxy:
        merged = self.df.join(other.df, on=["datetime", "vt_symbol"], suffixes=("", "_r"))
        result = merged.with_columns(
            (pl.col("data") - pl.col("data").rolling_mean(window).over("vt_symbol")) *
            (pl.col("data_r") - pl.col("data_r").rolling_mean(window).over("vt_symbol"))
        ).select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_mean(window).over("vt_symbol").alias("data")
        )
        return DataProxy(result)

    def ts_slope(self, window: int) -> DataProxy:
        def _slope(s: pl.Series) -> float:
            x = np.arange(len(s))
            y = s.to_numpy()
            if len(y) < 2 or np.all(y == y[0]):
                return 0.0
            return float(np.polyfit(x, y, 1)[0])
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_map(_slope, window).over("vt_symbol").alias("data")
        ))

    def ts_decay_linear(self, window: int) -> DataProxy:
        def _decay(s: pl.Series) -> float:
            n = len(s)
            weights = np.arange(1, n + 1, dtype=float)
            return float(np.dot(s.to_numpy(), weights) / weights.sum())
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_map(_decay, window).over("vt_symbol").alias("data")
        ))

    def ts_argmax(self, window: int) -> DataProxy:
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_map(lambda s: int(s.arg_max()) + 1, window).over("vt_symbol").alias("data")
        ))

    def ts_argmin(self, window: int) -> DataProxy:
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_map(lambda s: int(s.arg_min()) + 1, window).over("vt_symbol").alias("data")
        ))

    def ts_delta(self, window: int) -> DataProxy:
        return self - self.ts_delay(window)

    def ts_product(self, window: int) -> DataProxy:
        return DataProxy(self.df.select(
            pl.col("datetime"), pl.col("vt_symbol"),
            pl.col("data").rolling_map(lambda s: float(np.prod(s.to_numpy())), window).over("vt_symbol").alias("data")
        ))


# ── Cross-section operators ─────────────────────────────────────────

def cs_rank(feature: DataProxy) -> DataProxy:
    """Cross-sectional rank (0=lowest, 1=highest)."""
    min_v = feature.df["data"].min()
    max_v = feature.df["data"].max()
    if max_v == min_v:
        return DataProxy(feature.df.with_columns(pl.lit(0.5).alias("data")))
    return DataProxy(feature.df.with_columns(
        ((pl.col("data") - min_v) / (max_v - min_v)).alias("data")
    ))


def cs_mean(feature: DataProxy) -> DataProxy:
    return DataProxy(feature.df.with_columns(
        pl.col("data").mean().over("datetime").alias("data")
    ))


def cs_std(feature: DataProxy) -> DataProxy:
    return DataProxy(feature.df.with_columns(
        pl.col("data").std().over("datetime").alias("data")
    ))


def cs_sum(feature: DataProxy) -> DataProxy:
    return DataProxy(feature.df.with_columns(
        pl.col("data").sum().over("datetime").alias("data")
    ))


def cs_scale(feature: DataProxy) -> DataProxy:
    """Z-score normalization per cross-section."""
    mean = feature.df["data"].mean()
    std = feature.df["data"].std()
    if std == 0:
        return DataProxy(feature.df.with_columns(pl.lit(0.0).alias("data")))
    return DataProxy(feature.df.with_columns(
        ((pl.col("data") - mean) / std).alias("data")
    ))


# ── Expression engine ───────────────────────────────────────────────

_TS_OPS = {
    "ts_delay": lambda f, w: f.ts_delay(w),
    "ts_min": lambda f, w: f.ts_min(w),
    "ts_max": lambda f, w: f.ts_max(w),
    "ts_sum": lambda f, w: f.ts_sum(w),
    "ts_mean": lambda f, w: f.ts_mean(w),
    "ts_std": lambda f, w: f.ts_std(w),
    "ts_rank": lambda f, w: f.ts_rank(w),
    "ts_slope": lambda f, w: f.ts_slope(w),
    "ts_decay_linear": lambda f, w: f.ts_decay_linear(w),
    "ts_argmax": lambda f, w: f.ts_argmax(w),
    "ts_argmin": lambda f, w: f.ts_argmin(w),
    "ts_delta": lambda f, w: f.ts_delta(w),
    "ts_product": lambda f, w: f.ts_product(w),
    "ts_corr": lambda f1, f2, w: f1.ts_corr(f2, w),
    "ts_cov": lambda f1, f2, w: f1.ts_cov(f2, w),
}

_CS_OPS = {
    "cs_rank": cs_rank,
    "cs_mean": cs_mean,
    "cs_std": cs_std,
    "cs_sum": cs_sum,
    "cs_scale": cs_scale,
}

_MATH_OPS = {
    "abs": lambda f: abs(f),
    "log": lambda f: DataProxy(f.df.with_columns(pl.col("data").log().alias("data"))),
    "sign": lambda f: DataProxy(f.df.with_columns(
        pl.when(pl.col("data") > 0).then(1).when(pl.col("data") < 0).then(-1).otherwise(0).alias("data")
    )),
    "less": lambda a, b: a if isinstance(a, DataProxy) and isinstance(b, DataProxy) and (a < b) else (a < b),
    "greater": lambda a, b: a if isinstance(a, DataProxy) and isinstance(b, DataProxy) and (a > b) else (a > b),
}


def register_ts_operator(name: str, fn: Any) -> None:
    """Register a custom time-series operator for use in expressions."""
    _TS_OPS[name] = fn


def register_cs_operator(name: str, fn: Any) -> None:
    """Register a custom cross-section operator."""
    _CS_OPS[name] = fn


def calculate_expression(df: pl.DataFrame, expression: str) -> pl.DataFrame:
    """Evaluate a factor expression string against a Polars DataFrame.

    The DataFrame must contain columns ``["datetime", "vt_symbol"]`` and
    any columns referenced in the expression (e.g. ``close``, ``volume``).

    Expression syntax supports:
    - Arithmetic: ``+``, ``-``, ``*``, ``/``, ``**``
    - TS operators: ``ts_sum(close, 5)``, ``ts_mean(close, 20)``
    - CS operators: ``cs_rank(close)``, ``cs_scale(close)``
    - Math: ``abs(close)``, ``log(close)``, ``sign(close)``

    Examples:
        >>> df = pl.DataFrame({"datetime": [...], "vt_symbol": [...], "close": [...], "volume": [...]})
        >>> result = calculate_expression(df, "ts_sum(close, 5) / ts_mean(close, 20)")
        >>> result  # pl.DataFrame with ["datetime", "vt_symbol", "data"]

        >>> result = calculate_expression(df, "ts_corr(close, volume, 10)")
    """
    d: dict[str, Any] = {}

    # Inject operators into local namespace
    d.update(_TS_OPS)
    d.update(_CS_OPS)
    d.update(_MATH_OPS)

    # Create DataProxy for each feature column
    for col in df.columns:
        if col in ("datetime", "vt_symbol"):
            continue
        col_df = df[["datetime", "vt_symbol", col]]
        d[col] = DataProxy(col_df, col)

    try:
        result: DataProxy = eval(expression, {"__builtins__": {}}, d)
        return result.df
    except Exception as exc:
        logger.error("Expression evaluation failed: %s\nExpression: %s", exc, expression)
        raise


def to_datetime(arg: datetime | str) -> datetime:
    if isinstance(arg, str):
        fmt = "%Y-%m-%d" if "-" in arg else "%Y%m%d"
        return datetime.strptime(arg, fmt)
    return arg


__all__ = [
    "DataProxy",
    "calculate_expression",
    "register_ts_operator",
    "register_cs_operator",
    "to_datetime",
]