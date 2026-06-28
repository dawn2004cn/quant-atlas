from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from app.modules.strategy.logic.base import IStrategyLogic

class RSIReversionStrategy(IStrategyLogic):
    """RSI Reversion logic: RSI < Oversold = Long, RSI > Overbought = Short."""

    def compute_signals(self, data: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        period = params.get("rsi_period", 14)
        overbought = params.get("overbought", 70)
        oversold = params.get("oversold", 30)

        if 'close' not in data.columns:
            return pd.Series(0, index=data.index)

        delta = data['close'].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        signals = pd.Series(0, index=data.index)
        signals[rsi < oversold] = 1
        signals[rsi > overbought] = -1
        return signals

    def get_description(self, params: dict[str, Any]) -> str:
        return f"Mean Reversion: RSI({params.get('rsi_period')}) with boundaries {params.get('oversold')}/{params.get('overbought')}"
