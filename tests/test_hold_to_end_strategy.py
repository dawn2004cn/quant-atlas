"""Hold-to-end strategy used by legacy ``scripts/backtest_engine`` tests."""

from __future__ import annotations

import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parents[1] / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

import pandas as pd

from trading_strategies import BaseTradingStrategy


class HoldToEndStrategy(BaseTradingStrategy):
    """Buy near the end of the backtest window and hold."""

    @property
    def name(self) -> str:
        return "HoldToEnd"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        data["Signal"] = 0
        if len(data) > 1:
            data.iloc[-2, data.columns.get_loc("Signal")] = 1
        return data

    def get_start_idx(self) -> int:
        return 1


__all__ = ["HoldToEndStrategy"]
