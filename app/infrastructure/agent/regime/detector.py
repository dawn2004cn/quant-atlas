from __future__ import annotations

"""Market Regime Detection Engine.

Uses statistical methods to identify current market state (Bull, Bear, Volatile).
"""


from typing import Any

import pandas as pd

from app.core.logger import get_logger

logger = get_logger(__name__)

class MarketRegimeDetector:
    """Detects current market regime based on OHLCV data."""

    def __init__(self):
        self.current_regime = "NEUTRAL"

    def detect(self, price_data: pd.DataFrame) -> str:
        """
        Simple regime detection based on Moving Averages and Volatility.
        Returns: 'BULL', 'BEAR', 'VOLATILE', 'NEUTRAL'
        """
        if len(price_data) < 20:
            return "NEUTRAL"

        sma_20 = price_data['Close'].rolling(window=20).mean()
        volatility = price_data['Close'].pct_change().rolling(window=20).std()

        current_price = price_data['Close'].iloc[-1]
        current_sma = sma_20.iloc[-1]
        current_vol = volatility.iloc[-1]

        # Logic for regime shift
        if current_vol > 0.02: # Volatility threshold
            return "VOLATILE"
        elif current_price > current_sma:
            return "BULL"
        elif current_price < current_sma:
            return "BEAR"
        else:
            return "NEUTRAL"

class StrategyEvolver:
    """Evolves strategy parameters based on detected regime."""

    def __init__(self, strategy_config: dict[str, Any]):
        self.config = strategy_config

    def evolve(self, regime: str) -> dict[str, Any]:
        """Adjust parameters based on market regime."""
        new_config = self.config.copy()

        if regime == "BULL":
            new_config["risk_tolerance"] = 0.8
            new_config["position_sizing"] = "aggressive"
        elif regime == "BEAR":
            new_config["risk_tolerance"] = 0.3
            new_config["position_sizing"] = "conservative"
        elif regime == "VOLATILE":
            new_config["stop_loss_pct"] = 0.05
            new_config["leverage"] = 1.0

        logger.info(f"Strategy evolved to regime {regime}: {new_config}")
        return new_config
