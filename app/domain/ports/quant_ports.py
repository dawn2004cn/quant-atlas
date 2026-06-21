from __future__ import annotations
"""Backtest engine domain interfaces."""

from abc import ABC, abstractmethod
from typing import Any, Dict

class IBacktestEngine(ABC):
    """Abstraction for a pluggable backtesting engine."""
    
    @abstractmethod
    def run(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a backtest."""
        raise NotImplementedError
