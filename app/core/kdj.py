"""KDJ lines aligned with A-share (通达信) naming."""

from __future__ import annotations

import pandas as pd
from ta.momentum import StochasticOscillator


def tdx_k_d(stoch: StochasticOscillator) -> tuple[pd.Series, pd.Series]:
    """Return (K, D) per 通达信: K = ta ``stoch_signal``, D = ta ``stoch``."""
    return stoch.stoch_signal(), stoch.stoch()


def tdx_k_d_j(stoch: StochasticOscillator) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (K, D, J) with J = 3K - 2D."""
    k, d = tdx_k_d(stoch)
    return k, d, 3 * k - 2 * d
