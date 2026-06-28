from __future__ import annotations
"""WebSocket port for real-time market data."""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections.abc import Callable


@dataclass
class QuoteUpdate:
    """Real-time quote update."""
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    timestamp: str


@dataclass
class Subscription:
    """Subscription to real-time data."""
    symbols: list[str]
    channels: list[str] = field(default_factory=lambda: ["ticker"])


class WebSocketPort(ABC):
    """Port for WebSocket real-time data."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish WebSocket connection."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Close WebSocket connection."""
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, subscription: Subscription) -> bool:
        """Subscribe to symbols/channels."""
        raise NotImplementedError

    @abstractmethod
    def unsubscribe(self, subscription: Subscription) -> bool:
        """Unsubscribe from symbols/channels."""
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        raise NotImplementedError

    def on_message(self, callback: Callable[[QuoteUpdate], None]) -> None:
        """Set callback for incoming messages."""
        self._message_callback = callback

    def on_error(self, callback: Callable[[str], None]) -> None:
        """Set callback for errors."""
        self._error_callback = callback


class MockWebSocketAdapter(WebSocketPort):
    """Mock WebSocket adapter for testing."""

    def __init__(self):
        self._connected = False
        self._subscriptions: set[str] = set()
        self._message_callback: Callable[[QuoteUpdate], None] | None = None
        self._error_callback: Callable[[str], None] | None = None

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def subscribe(self, subscription: Subscription) -> bool:
        if not self._connected:
            return False
        for sym in subscription.symbols:
            self._subscriptions.add(sym)
        return True

    def unsubscribe(self, subscription: Subscription) -> bool:
        for sym in subscription.symbols:
            self._subscriptions.discard(sym)
        return True

    def is_connected(self) -> bool:
        return self._connected

    def simulate_update(self, symbol: str, price: float, change: float, volume: int) -> None:
        """Simulate a quote update for testing."""
        if self._message_callback and symbol in self._subscriptions:
            change_pct = (change / price * 100) if price > 0 else 0
            update = QuoteUpdate(
                symbol=symbol,
                price=price,
                change=change,
                change_pct=change_pct,
                volume=volume,
                timestamp="",
            )
            self._message_callback(update)
