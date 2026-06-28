from __future__ import annotations

from typing import Any
import pandas as pd
from app.modules.strategy.logic.base import IStrategyLogic

class SentimentAdaptiveStrategy(IStrategyLogic):
    """AI Sentiment Adaptive: Adjusts bias based on external sentiment score."""

    def compute_signals(self, data: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        # In a real scenario, sentiment is a column in the DataFrame provided by the lake
        sentiment_threshold = params.get("sentiment_threshold", 0.6)

        if 'sentiment' not in data.columns:
            # Fallback: assume neutral if sentiment column is missing
            return pd.Series(0, index=data.index)

        signals = pd.Series(0, index=data.index)
        signals[data['sentiment'] > sentiment_threshold] = 1
        signals[data['sentiment'] < (1 - sentiment_threshold)] = -1
        return signals

    def get_description(self, params: dict[str, Any]) -> str:
        return f"AI Adaptive: Sentiment threshold at {params.get('sentiment_threshold')}"
