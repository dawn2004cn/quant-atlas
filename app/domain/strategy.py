from __future__ import annotations

"""Strategy interface and base class (Freqtrade port)."""


from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from app.domain.trading_entities import Trade


class BaseStrategy(ABC):
    """Base class for trading strategies."""

    timeframe: str = "5m"
    stoploss: float = -0.10
    minimal_roi: dict[str, float] = {
        "0": 0.05
    }

    @abstractmethod
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
        """Calculate indicators for the given dataframe."""
        raise NotImplementedError

    @abstractmethod
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
        """Add entry signals to the dataframe."""
        raise NotImplementedError

    @abstractmethod
    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
        """Add exit signals to the dataframe."""
        raise NotImplementedError

    def check_roi(self, trade: Trade, current_rate: float, current_time: float) -> bool:
        """Check if ROI condition is met."""
        profit_ratio = trade.calc_profit_ratio(current_rate)

        # Simple ROI check
        duration = (current_time - trade.open_date.timestamp()) / 60  # in minutes

        sorted_roi = sorted(self.minimal_roi.items(), key=lambda x: int(x[0]), reverse=True)
        for roi_time, roi_profit in sorted_roi:
            if duration >= int(roi_time) and profit_ratio >= roi_profit:
                return True
        return False

    def check_stoploss(self, trade: Trade, current_rate: float) -> bool:
        """Check if stoploss condition is met."""
        profit_ratio = trade.calc_profit_ratio(current_rate)
        if profit_ratio <= self.stoploss:
            return True
        return False


class SampleStrategy(BaseStrategy):
    """A sample strategy for testing the Freqtrade port."""

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
        dataframe["sma"] = dataframe["close"].rolling(window=20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
        dataframe.loc[
            (dataframe["close"] > dataframe["sma"]),
            "enter_long"
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
        dataframe.loc[
            (dataframe["close"] < dataframe["sma"]),
            "exit_long"
        ] = 1
        return dataframe
