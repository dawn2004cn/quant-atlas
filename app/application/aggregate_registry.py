from __future__ import annotations
"""Aggregate Registry - Manages domain aggregates in application layer.

Provides registry for stock and portfolio aggregates.
"""


import logging
from typing import Any, Optional

from app.domain.aggregates.stock_aggregate import StockAggregate, StockAggregateFactory
from app.domain.aggregates.portfolio_aggregate import PortfolioAggregate
from app.domain.aggregates.trading_session_aggregate import TradingSessionAggregate


from app.core.logger import get_logger

logger = get_logger(__name__)


class AggregateRegistry:
    """Registry for managing domain aggregates.
    
    Provides a way to access and manage aggregates
    within the application layer.
    """
    
    _instance: Optional["AggregateRegistry"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._stocks: dict[str, StockAggregate] = {}
            cls._instance._portfolios: dict[str, PortfolioAggregate] = {}
            cls._instance._sessions: dict[str, TradingSessionAggregate] = {}
        return cls._instance
    
    def create_stock(
        self,
        code: str,
        name: str,
        market: str = "A"
    ) -> StockAggregate:
        """Create and register a stock aggregate."""
        aggregate = StockAggregate.create(code, name, market)
        self._stocks[code] = aggregate
        logger.info(f"Created stock aggregate: {code}")
        return aggregate
    
    def get_stock(self, code: str) -> Optional[StockAggregate]:
        """Get a stock aggregate."""
        return self._stocks.get(code)
    
    def remove_stock(self, code: str) -> bool:
        """Remove a stock aggregate."""
        if code in self._stocks:
            del self._stocks[code]
            return True
        return False
    
    def create_portfolio(
        self,
        portfolio_id: str,
        initial_cash: float = 1000000.0
    ) -> PortfolioAggregate:
        """Create and register a portfolio aggregate."""
        aggregate = PortfolioAggregate.create(initial_cash)
        self._portfolios[portfolio_id] = aggregate
        logger.info(f"Created portfolio aggregate: {portfolio_id}")
        return aggregate
    
    def get_portfolio(self, portfolio_id: str) -> Optional[PortfolioAggregate]:
        """Get a portfolio aggregate."""
        return self._portfolios.get(portfolio_id)
    
    def remove_portfolio(self, portfolio_id: str) -> bool:
        """Remove a portfolio aggregate."""
        if portfolio_id in self._portfolios:
            del self._portfolios[portfolio_id]
            return True
        return False
    
    def create_trading_session(
        self,
        session_id: str
    ) -> TradingSessionAggregate:
        """Create and register a trading session aggregate."""
        aggregate = TradingSessionAggregate.create()
        self._sessions[session_id] = aggregate
        logger.info(f"Created trading session: {session_id}")
        return aggregate
    
    def get_trading_session(self, session_id: str) -> Optional[TradingSessionAggregate]:
        """Get a trading session aggregate."""
        return self._sessions.get(session_id)
    
    def list_stocks(self) -> list[str]:
        """List all stock aggregate IDs."""
        return list(self._stocks.keys())
    
    def list_portfolios(self) -> list[str]:
        """List all portfolio aggregate IDs."""
        return list(self._portfolios.keys())
    
    def list_sessions(self) -> list[str]:
        """List all trading session IDs."""
        return list(self._sessions.keys())
    
    def get_stats(self) -> dict:
        """Get registry statistics."""
        return {
            "stocks": len(self._stocks),
            "portfolios": len(self._portfolios),
            "sessions": len(self._sessions),
        }
    
    def clear(self) -> None:
        """Clear all aggregates."""
        self._stocks.clear()
        self._portfolios.clear()
        self._sessions.clear()
        logger.info("Aggregate registry cleared")


def get_aggregate_registry() -> AggregateRegistry:
    """Get global aggregate registry."""
    return AggregateRegistry()


def get_stock(code: str) -> Optional[StockAggregate]:
    """Convenience function to get stock aggregate."""
    return get_aggregate_registry().get_stock(code)


def get_portfolio(portfolio_id: str) -> Optional[PortfolioAggregate]:
    """Convenience function to get portfolio aggregate."""
    return get_aggregate_registry().get_portfolio(portfolio_id)


def get_session(session_id: str) -> Optional[TradingSessionAggregate]:
    """Convenience function to get trading session."""
    return get_aggregate_registry().get_trading_session(session_id)


__all__ = [
    "AggregateRegistry",
    "get_aggregate_registry",
    "get_stock",
    "get_portfolio",
    "get_session",
]