from __future__ import annotations

from typing import Any

import pandas as pd

from app.modules.strategy.logic.base import IStrategyLogic


class MomentumAlphaStrategy(IStrategyLogic):
    """Momentum Alpha: Price breakout combined with volume surge."""

    def compute_signals(self, data: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        lookback = params.get("lookback_period", 5)
        vol_mult = params.get("volume_multiplier", 2.0)

        if 'close' not in data.columns or 'volume' not in data.columns:
            return pd.Series(0, index=data.index)

        price_breakout = data['close'] > data['close'].rolling(lookback).max().shift(1)
        vol_surge = data['volume'] > data['volume'].rolling(lookback).mean() * vol_mult

        signals = pd.Series(0, index=data.index)
        signals[price_breakout & vol_surge] = 1
        return signals

    def get_description(self, params: dict[str, Any]) -> str:
        return f"Quant Factor: Price breakout over {params.get('lookback_period')} days with {params.get('volume_multiplier')}x volume surge"
