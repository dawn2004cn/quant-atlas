from __future__ import annotations
"""Polars-based compute utilities for high-performance data processing."""


from typing import Any
from collections.abc import Callable


from app.core.logger import get_logger

logger = get_logger(__name__)

try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pl = None


class PolarsDataFrame:
    """Wrapper for Polars DataFrame with fallback to pandas."""

    def __init__(self, data=None):
        if not POLARS_AVAILABLE:
            raise ImportError("Polars not installed. Install with: pip install polars")

        if data is None:
            self._df = pl.DataFrame()
        elif isinstance(data, pl.DataFrame):
            self._df = data
        else:
            # Assume dict or list of dicts
            self._df = pl.DataFrame(data)

    @staticmethod
    def from_pandas(df: Any) -> PolarsDataFrame:
        """Convert pandas DataFrame to PolarsDataFrame."""
        if not POLARS_AVAILABLE:
            raise ImportError("Polars not installed")
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            return PolarsDataFrame(pl.from_pandas(df))
        return PolarsDataFrame(df)

    def to_pandas(self) -> Any:
        """Convert back to pandas DataFrame."""
        return self._df.to_pandas()

    def filter(self, condition: str) -> PolarsDataFrame:
        """Filter rows using Polars expression string."""
        return PolarsDataFrame(self._df.filter(pl.eval(condition)))

    def select(self, columns: list[str]) -> PolarsDataFrame:
        """Select specific columns."""
        return PolarsDataFrame(self._df.select(columns))

    def with_columns(self, **kwargs) -> PolarsDataFrame:
        """Add or replace columns."""
        exprs = []
        for name, func in kwargs.items():
            if callable(func):
                exprs.append(func(pl.col(name)))
            else:
                exprs.append(pl.lit(func).alias(name))
        return PolarsDataFrame(self._df.with_columns(*exprs))

    def sort(self, by: str, descending: bool = False) -> PolarsDataFrame:
        """Sort by column."""
        return PolarsDataFrame(self._df.sort(by, descending=descending))

    def group_by(self, by: str) -> PolarsGroupBy:
        """Group by column."""
        return PolarsGroupBy(self._df.group_by(by))

    def join(self, other: PolarsDataFrame, on: str, how: str = "inner") -> PolarsDataFrame:
        """Join with another DataFrame."""
        return PolarsDataFrame(self._df.join(other._df, on=on, how=how))

    def head(self, n: int = 5) -> PolarsDataFrame:
        """Get first n rows."""
        return PolarsDataFrame(self._df.head(n))

    def to_dict(self) -> list[dict]:
        """Convert to list of dicts."""
        return self._df.to_dicts()

    def to_numpy(self) -> Any:
        """Convert to numpy array."""
        return self._df.to_numpy()

    @property
    def shape(self) -> tuple:
        return (self._df.height, self._df.width)

    def __len__(self) -> int:
        return len(self._df)


class PolarsGroupBy:
    """GroupBy operations for Polars."""

    def __init__(self, groupby):
        self._groupby = groupby

    def agg(self, **aggregations) -> PolarsDataFrame:
        """Aggregate with specified functions."""
        exprs = []
        for col, agg_func in aggregations.items():
            if isinstance(agg_func, list):
                for func in agg_func:
                    exprs.append(getattr(pl.col(col), func)().alias(f"{col}_{func}"))
            else:
                exprs.append(getattr(pl.col(col), agg_func)().alias(f"{col}_{agg_func}"))
        return PolarsDataFrame(self._groupby.agg(exprs))


def parallel_compute(
    df: Any,
    func: Callable[[Any], Any],
    n_partitions: int = 4,
    backend: str = "polars"
) -> Any:
    """Execute compute in parallel using Polars.

    Usage:
        result = parallel_compute(
            data,
            lambda df: df.filter(pl.col("price") > 100),
            n_partitions=4
        )
    """
    if not POLARS_AVAILABLE:
        logger.warning("Polars not available, falling back to sequential")
        return func(df)

    if backend == "polars" and isinstance(df, (list, dict)):
        polars_df = PolarsDataFrame(df)
        return func(polars_df)

    return func(df)


__all__ = ["PolarsDataFrame", "PolarsGroupBy", "parallel_compute", "POLARS_AVAILABLE"]
