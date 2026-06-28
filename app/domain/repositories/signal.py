from __future__ import annotations
"""Signal Repository Interface.

Defines the contract for signal data access.
"""


from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from app.domain.base import Entity


class SignalType(str, Enum):
    """Signal types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class Signal(Entity):
    """Signal entity domain model."""

    def __init__(
        self,
        stock_code: str,
        signal_type: SignalType,
        source: str,
        confidence: float,
        reason: str,
        **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.stock_code = stock_code
        self.signal_type = signal_type
        self.source = source
        self.confidence = confidence
        self.reason = reason
        self.expires_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_bullish(self) -> bool:
        return self.signal_type in (SignalType.BUY, SignalType.STRONG_BUY)

    @property
    def is_bearish(self) -> bool:
        return self.signal_type in (SignalType.SELL, SignalType.STRONG_SELL)


class ISignalRepository(ABC):
    """Signal repository interface."""

    @abstractmethod
    def get_by_stock(self, stock_code: str, limit: int = 10) -> list[Signal]:
        """Get signals for a stock."""
        pass

    @abstractmethod
    def get_active(self, limit: int = 100) -> list[Signal]:
        """Get active (non-expired) signals."""
        pass

    @abstractmethod
    def save(self, signal: Signal) -> Signal:
        """Save a signal."""
        pass

    @abstractmethod
    def delete_expired(self) -> int:
        """Delete expired signals, return count."""
        pass


__all__ = ["SignalType", "Signal", "ISignalRepository"]
