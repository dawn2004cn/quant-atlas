from __future__ import annotations
"""Factor registry and mining engine."""

from typing import Any, Callable, Dict, List
import pandas as pd
import quant_core

class FactorRegistry:
    """Central registry for factor calculation functions."""

    def __init__(self):
        self._factors: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        self._factors[name] = func

    def calculate(self, name: str, data: pd.DataFrame, **kwargs) -> pd.Series:
        if name not in self._factors:
            raise ValueError(f"Factor {name} not registered")
        return self._factors[name](data, **kwargs)

# Initialize registry and register native indicators
factor_registry = FactorRegistry()

def sma_factor(data: pd.DataFrame, window: int = 20) -> pd.Series:
    closes = data["close"].tolist()
    res = quant_core.calculate_sma(closes, window)
    return pd.Series(res, index=data.index)

def rsi_factor(data: pd.DataFrame, window: int = 14) -> pd.Series:
    closes = data["close"].tolist()
    res = quant_core.calculate_rsi(closes, window)
    return pd.Series(res, index=data.index)

factor_registry.register("sma", sma_factor)
factor_registry.register("rsi", rsi_factor)
