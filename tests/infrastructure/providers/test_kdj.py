"""KDJ indicator alignment with A-share (TDX) naming."""

from __future__ import annotations

import pandas as pd

from app.infrastructure.providers.indicators import AdvancedTaIndicatorProvider


def test_calc_kdj_swaps_ta_lines_to_tdx_k_d():
    """K (通达信) should be the smoother line — ta stoch_signal, not raw stoch."""
    n = 30
    high = pd.Series(range(10, 10 + n), dtype=float)
    low = high - 2
    close = high - 1
    k, d, j = AdvancedTaIndicatorProvider.calc_kdj(high, low, close)
    stoch = __import__("ta.momentum", fromlist=["StochasticOscillator"]).StochasticOscillator(
        high=high, low=low, close=close, window=9, smooth_window=3
    )
    assert k.equals(stoch.stoch_signal())
    assert d.equals(stoch.stoch())
    assert j.equals(3 * k - 2 * d)
