"""KDJ TDX naming tests."""

from __future__ import annotations

import pandas as pd
from ta.momentum import StochasticOscillator

from app.core.kdj import tdx_k_d, tdx_k_d_j
from app.infrastructure.providers.indicators import AdvancedTaIndicatorProvider


def test_tdx_k_d_matches_provider_calc_kdj():
    n = 30
    high = pd.Series(range(10, 10 + n), dtype=float)
    low = high - 2
    close = high - 1
    stoch = StochasticOscillator(high=high, low=low, close=close, window=9, smooth_window=3)
    k, d = tdx_k_d(stoch)
    pk, pd_, pj = AdvancedTaIndicatorProvider.calc_kdj(high, low, close)
    assert k.equals(pk)
    assert d.equals(pd_)
    kj, dj, jj = tdx_k_d_j(stoch)
    assert kj.equals(pk)
    assert dj.equals(pd_)
    assert jj.equals(pj)
