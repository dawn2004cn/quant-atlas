from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.strategy.logic.base import IStrategyLogic


class MovingAverageCrossStrategy(IStrategyLogic):
    """Classic MA Crossover logic: Fast MA > Slow MA = Long."""

    def compute_signals(self, data: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        fast_ma = params.get("fast_ma", 20)
        slow_ma = params.get("slow_ma", 60)

        if 'close' not in data.columns:
            return pd.Series(0, index=data.index)

        fast = data['close'].rolling(window=fast_ma).mean()
        slow = data['close'].rolling(window=slow_ma).mean()

        signals = pd.Series(0, index=data.index)
        signals[fast > slow] = 1
        signals[fast < slow] = -1
        return signals

    def get_description(self, params: dict[str, Any]) -> str:
        return f"Trend Following: Fast MA({params.get('fast_ma')}) crossing Slow MA({params.get('slow_ma')})"
