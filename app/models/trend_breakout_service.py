"""Service layer for trend breakout strategies.

Provides higher-level orchestration, strategy lifecycle management,
and batch signal generation for trend breakout models.

All pure-model classes and computation lives in trend_breakout_model.py.
"""

from __future__ import annotations

import pandas as pd

from ..core.base_strategy import BaseTradingStrategy
from .trend_breakout_model import CANSLIMModelStrategy


class CANSLIMService:
    """Service wrapper for CANSLIM strategy with data-fetching guidance.

    The CANSLIM strategy requires both technical (OHLCV) and fundamental
    (net_profit_growth) data. This service provides helper methods for
    orchestrating the data merge before signal generation.
    """

    @staticmethod
    def merge_fundamentals(
        df_kline: pd.DataFrame,
        df_finance: pd.DataFrame,
        date_col: str = "Date",
        growth_col: str = "net_profit_growth",
    ) -> pd.DataFrame:
        """Merge quarterly fundamental data into daily OHLCV data using forward-fill.

        Parameters
        ----------
        df_kline : pd.DataFrame
            Daily OHLCV DataFrame with a Date column.
        df_finance : pd.DataFrame
            Quarterly financial data with a Report_Date and net_profit_growth column.
        date_col : str
            Name of the date column in df_kline.
        growth_col : str
            Name of the growth-rate column to merge.

        Returns
        -------
        pd.DataFrame
            Merged DataFrame with forward-filled fundamental data.
        """
        result = pd.merge(
            df_kline,
            df_finance[['Report_Date', growth_col]],
            left_on=date_col,
            right_on='Report_Date',
            how='left',
        )
        result[growth_col] = result[growth_col].ffill().fillna(0)
        return result

    @staticmethod
    def generate_signals(
        strategy: CANSLIMModelStrategy,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate CANSLIM signals, handling optional fundamental data gracefully."""
        return strategy.generate_signals(df)


class TrendBreakoutService:
    """Aggregate service for trend breakout strategy lifecycle management.

    Provides convenience methods for running multiple breakout strategies
    against the same dataset.
    """

    def __init__(self) -> None:
        self._strategies: list[BaseTradingStrategy] = []

    def load_strategies(self, strategies: list[BaseTradingStrategy]) -> None:
        """Load strategy instances for batch evaluation."""
        self._strategies = strategies

    def batch_generate_signals(
        self,
        df: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:
        """Run generate_signals for all loaded strategies.

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV data for signal generation.

        Returns
        -------
        dict[str, pd.DataFrame]
            Mapping of strategy name -> signal DataFrame.
        """
        results: dict[str, pd.DataFrame] = {}
        for strategy in self._strategies:
            try:
                sig_df = strategy.generate_signals(df.copy())
                results[strategy.name] = sig_df
            except Exception:
                continue
        return results


__all__ = [
    "CANSLIMService",
    "TrendBreakoutService",
]
