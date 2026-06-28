from __future__ import annotations

"""Backtest engine domain interfaces."""

from abc import ABC, abstractmethod
from typing import Any


class IBacktestEngine(ABC):
    """Abstraction for a pluggable backtesting engine."""

    @abstractmethod
    def run(self, strategy_config: dict[str, Any]) -> dict[str, Any]:
        """Execute a backtest."""
        raise NotImplementedError
