from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd

class IStrategyLogic(ABC):
    """
    Interface for all strategy logic implementations.
    Ensures that templates in the Wizard can be instantiated and executed.
    """

    @abstractmethod
    def compute_signals(self, data: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        """
        Compute a signal series (e.g., 1 for Long, -1 for Short, 0 for Flat).
        """
        pass

    @abstractmethod
    def get_description(self, params: dict[str, Any]) -> str:
        """Return a human-readable description of the current configuration."""
        pass
