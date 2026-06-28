from __future__ import annotations
"""Stock Repository Interface.

Defines the contract for stock data access.
"""


from abc import ABC, abstractmethod
from typing import Any

from app.domain.base import Entity


class Stock(Entity):
    """Stock entity domain model."""

    def __init__(
        self,
        code: str,
        name: str,
        market: str,
        **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.code = code
        self.name = name
        self.market = market

    @property
    def is_active(self) -> bool:
        return self.market in ("A", "HK", "US")


class IStockRepository(ABC):
    """Stock repository interface."""

    @abstractmethod
    def get_by_code(self, code: str) -> Stock | None:
        """Get stock by code."""
        pass

    @abstractmethod
    def list_by_market(self, market: str, limit: int = 100) -> list[Stock]:
        """List stocks by market."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[Stock]:
        """Search stocks by name or code."""
        pass


class MarketData(Entity):
    """Market data entity."""

    def __init__(
        self,
        stock_code: str,
        date: str,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int = 0,
        **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.stock_code = stock_code
        self.date = date
        self.open = open_price
        self.high = high_price
        self.low = low_price
        self.close = close_price
        self.volume = volume

    @property
    def change(self) -> float:
        return ((self.close - self.open) / self.open) * 100 if self.open else 0


class IMarketDataRepository(ABC):
    """Market data repository interface."""

    @abstractmethod
    def get_daily(self, code: str, start_date: str, end_date: str) -> list[MarketData]:
        """Get daily market data."""
        pass

    @abstractmethod
    def get_latest(self, code: str) -> MarketData | None:
        """Get latest market data."""
        pass


__all__ = ["Stock", "IStockRepository", "MarketData", "IMarketDataRepository"]
