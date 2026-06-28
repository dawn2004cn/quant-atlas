"""Domain Repositories - Interface definitions.

This module exports all repository interfaces for the domain layer.
"""

from app.domain.repositories.signal import (
    ISignalRepository,
    Signal,
    SignalType,
)
from app.domain.repositories.stock import (
    IMarketDataRepository,
    IStockRepository,
    MarketData,
    Stock,
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
