"""RSI should use Wilder EWM smoothing (industry standard)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.modules.strategy.logic.reversion import RSIReversionStrategy


def _sma_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def test_rsi_reversion_uses_wilder_smoothing() -> None:
    rng = np.random.default_rng(42)
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, size=80)))
    data = pd.DataFrame({"close": close})

    strategy = RSIReversionStrategy()
    signals = strategy.compute_signals(data, {"rsi_period": 14})

    wilder = _wilder_rsi(close, 14)
    sma = _sma_rsi(close, 14)

    # Strategy thresholds should align with Wilder RSI, not SMA RSI.
    diff = (wilder.dropna() - sma.dropna()).abs()
    assert float(diff.max()) > 0.01
    for idx in wilder[wilder < 30].index:
        assert int(signals.loc[idx]) == 1
    for idx in wilder[wilder > 70].index:
        assert int(signals.loc[idx]) == -1
