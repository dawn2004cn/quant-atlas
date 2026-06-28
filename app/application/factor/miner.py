from __future__ import annotations

"""Automated Factor Mining Engine."""

from typing import Any

import pandas as pd

from app.application.factor.registry import factor_registry
from app.core.logger import get_logger

logger = get_logger(__name__)

class FactorMiner:
    """Evaluates and scores factors."""

    def __init__(self, registry=factor_registry):
        self._registry = registry

    def score_factor(self, factor_name: str, data: pd.DataFrame, target: pd.Series, **kwargs) -> float:
        """Calculate IC (Information Coefficient) for a factor."""
        factor_series = self._registry.calculate(factor_name, data, **kwargs)

        # Align data
        df = pd.concat([factor_series.rename("factor"), target.rename("target")], axis=1).dropna()

        # Calculate IC
        ic = df["factor"].corr(df["target"])
        return float(ic)

    def mine(self, data: pd.DataFrame, target: pd.Series, factors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Mine and rank factors."""
        results = []
        for f in factors:
            name = f["name"]
            params = f.get("params", {})
            try:
                score = self.score_factor(name, data, target, **params)
                results.append({"name": name, "params": params, "ic": score})
            except Exception as e:
                logger.error(f"Mining factor {name} failed: {e}")

        return sorted(results, key=lambda x: abs(x["ic"]), reverse=True)
