"""Domain Repositories - Interface definitions.

This module exports all repository interfaces for the domain layer.
"""

from app.domain.repositories.stock import (
    Stock,
    IStockRepository,
    MarketData,
    IMarketDataRepository,
)
from app.domain.repositories.signal import (
    SignalType,
    Signal,
    ISignalRepository,
)

__all__ = [
    # Stock
    "Stock",
    "IStockRepository",
    "MarketData",
    "IMarketDataRepository",
    # Signal
    "SignalType",
    "Signal",
    "ISignalRepository",
]
