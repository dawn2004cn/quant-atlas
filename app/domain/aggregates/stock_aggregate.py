from __future__ import annotations
"""Stock Aggregate Root.

Aggregate root for stock with market data and signals.
"""


from typing import Any

from app.domain.base import AggregateRoot
from app.domain.repositories.stock import Stock, MarketData
from app.domain.repositories.signal import Signal, SignalType


class StockAggregateError(Exception):
    """Stock aggregate error."""
    pass


class InvalidStockCodeError(StockAggregateError):
    """Invalid stock code."""
    pass


class DuplicateSignalError(StockAggregateError):
    """Duplicate signal error."""
    pass


class StockAggregate(AggregateRoot):
    """Stock aggregate root.

    Encapsulates:
    - Stock entity
    - Market data history
    - Signals
    - Invariants: valid code, consistent data
    """

    def __init__(
        self,
        stock: Stock,
        market_data: list[MarketData] = None,
        signals: list[Signal] = None,
        latest_price: float = None,
    ):
        if not stock.code or len(stock.code) < 6:
            raise InvalidStockCodeError(f"Invalid stock code: {stock.code}")

        self._stock = stock
        self._market_data = market_data or []
        self._signals = signals or []
        self._latest_price = latest_price
        super().__init__()

    @staticmethod
    def create(
        code: str,
        name: str,
        market: str = "A"
    ) -> StockAggregate:
        """Create a new stock aggregate."""
        if not code or len(code) < 6:
            raise InvalidStockCodeError(f"Invalid stock code: {code}")

        stock = Stock(code=code, name=name, market=market)
        return StockAggregate(stock=stock)

    @staticmethod
    def from_entity(stock: Stock) -> StockAggregate:
        """Create from existing stock entity."""
        if not stock.code or len(stock.code) < 6:
            raise InvalidStockCodeError(f"Invalid stock code: {stock.code}")
        return StockAggregate(stock=stock)

    @property
    def stock(self) -> Stock:
        return self._stock

    @property
    def code(self) -> str:
        return self._stock.code

    @property
    def name(self) -> str:
        return self._stock.name

    @property
    def market(self) -> str:
        return self._stock.market

    @property
    def is_active(self) -> bool:
        return self._stock.is_active

    @property
    def latest_price(self) -> float | None:
        return self._latest_price

    @property
    def market_data_count(self) -> int:
        return len(self._market_data)

    @property
    def signal_count(self) -> int:
        return len(self._signals)

    @property
    def active_signals(self) -> list[Signal]:
        return [s for s in self._signals if not s.is_expired]

    def add_market_data(self, data: MarketData) -> None:
        """Add market data to history."""
        if data.stock_code != self._stock.code:
            raise StockAggregateError(
                f"Code mismatch: {data.stock_code} != {self._stock.code}"
            )
        self._market_data.append(data)
        self._latest_price = data.close
        self.touch()

    def get_market_data(
        self,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> list[MarketData]:
        """Get market data in date range."""
        result = self._market_data

        if start_date:
            result = [d for d in result if d.date >= start_date]
        if end_date:
            result = [d for d in result if d.date <= end_date]

        return sorted(result, key=lambda d: d.date)

    def get_latest_market_data(self) -> MarketData | None:
        """Get latest market data."""
        if not self._market_data:
            return None
        return max(self._market_data, key=lambda d: d.date)

    def add_signal(self, signal: Signal) -> None:
        """Add a signal to the stock."""
        if signal.stock_code != self._stock.code:
            raise StockAggregateError(
                f"Code mismatch: {signal.stock_code} != {self._stock.code}"
            )

        existing = self._find_signal(signal)
        if existing:
            raise DuplicateSignalError(f"Signal already exists for {signal.stock_code}")

        self._signals.append(signal)
        self.touch()

    def _find_signal(self, signal: Signal) -> Signal | None:
        """Find existing signal."""
        for s in self._signals:
            if s.source == signal.source and s.signal_type == signal.signal_type:
                return s
        return None

    def get_signals(
        self,
        signal_type: SignalType | None = None,
        active_only: bool = False
    ) -> list[Signal]:
        """Get signals with optional filtering."""
        result = self._signals

        if signal_type:
            result = [s for s in result if s.signal_type == signal_type]

        if active_only:
            result = [s for s in result if not s.is_expired]

        return sorted(result, key=lambda s: s.created_at, reverse=True)

    def get_latest_signal(self) -> Signal | None:
        """Get the most recent signal."""
        if not self._signals:
            return None
        return max(self._signals, key=lambda s: s.created_at)

    def get_bullish_signals(self) -> list[Signal]:
        """Get all bullish signals."""
        return [s for s in self._signals if s.is_bullish]

    def get_bearish_signals(self) -> list[Signal]:
        """Get all bearish signals."""
        return [s for s in self._signals if s.is_bearish]

    def get_consensus(self) -> SignalType:
        """Get signal consensus."""
        bullish = len(self.get_bullish_signals())
        bearish = len(self.get_bearish_signals())

        if bullish > bearish:
            return SignalType.BUY
        elif bearish > bullish:
            return SignalType.SELL
        return SignalType.HOLD

    def clear_expired_signals(self) -> int:
        """Clear expired signals, return count."""
        before = len(self._signals)
        self._signals = [s for s in self._signals if not s.is_expired]
        return before - len(self._signals)

    def get_price_change(self) -> float:
        """Calculate price change percentage."""
        if not self._market_data or len(self._market_data) < 2:
            return 0.0

        latest = max(self._market_data, key=lambda d: d.date)
        earliest = min(self._market_data, key=lambda d: d.date)

        if earliest.open == 0:
            return 0.0

        return ((latest.close - earliest.open) / earliest.open) * 100

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "code": self.code,
            "name": self.name,
            "market": self.market,
            "latest_price": self.latest_price,
            "market_data_count": self.market_data_count,
            "signal_count": self.signal_count,
            "consensus": self.get_consensus().value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StockAggregateFactory:
    """Factory for creating stock aggregates."""

    @staticmethod
    def create_a_share(code: str, name: str) -> StockAggregate:
        """Create A-share stock aggregate."""
        return StockAggregate.create(code, name, market="A")

    @staticmethod
    def create_hk_share(code: str, name: str) -> StockAggregate:
        """Create HK stock aggregate."""
        return StockAggregate.create(code, name, market="HK")

    @staticmethod
    def create_us_share(code: str, name: str) -> StockAggregate:
        """Create US stock aggregate."""
        return StockAggregate.create(code, name, market="US")


__all__ = [
    "StockAggregate",
    "StockAggregateError",
    "InvalidStockCodeError",
    "DuplicateSignalError",
    "StockAggregateFactory",
]
