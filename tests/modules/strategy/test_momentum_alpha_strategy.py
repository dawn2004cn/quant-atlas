"""MomentumAlphaStrategy breakout logic tests."""

from __future__ import annotations

import pandas as pd

from app.modules.strategy.logic.factor import MomentumAlphaStrategy


def test_breakout_uses_prior_window_not_current_bar():
    """Close must exceed prior lookback high; flat series must not signal."""
    strategy = MomentumAlphaStrategy()
    closes = [10.0] * 12
    data = pd.DataFrame(
        {
            "close": closes,
            "volume": [1_000_000] * 12,
        }
    )
    signals = strategy.compute_signals(data, {"lookback_period": 5, "volume_multiplier": 1.0})
    assert (signals == 0).all()


def test_breakout_triggers_on_new_high_with_volume_surge():
    strategy = MomentumAlphaStrategy()
    closes = [10.0] * 10 + [11.0]
    volumes = [500_000] * 10 + [2_000_000]
    data = pd.DataFrame({"close": closes, "volume": volumes})
    signals = strategy.compute_signals(data, {"lookback_period": 5, "volume_multiplier": 1.5})
    assert int(signals.iloc[-1]) == 1
