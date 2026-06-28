from __future__ import annotations
"""CQRS Query Handlers.

Queries for reading domain state.
"""


import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Query:
    """Base query."""
    query_id: str = ""
    created_at: datetime = None

    def __post_init__(self):
        if not self.query_id:
            self.query_id = f"qry_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        if not self.created_at:
            self.created_at = datetime.now()


@dataclass
class GetStockQuery(Query):
    """Get a stock."""
    stock_code: str = ""


@dataclass
class GetPortfolioQuery(Query):
    """Get portfolio details."""
    portfolio_id: str = ""


@dataclass
class GetOrdersQuery(Query):
    """Get orders."""
    portfolio_id: str = ""
    status: str | None = None


@dataclass
class GetSignalsQuery(Query):
    """Get signals for stock."""
    stock_code: str = ""
    active_only: bool = False


@dataclass
class GetMarketDataQuery(Query):
    """Get market data."""
    stock_code: str = ""
    start_date: str | None = None
    end_date: str | None = None


@dataclass
class GetEventHistoryQuery(Query):
    """Get event history."""
    aggregate_id: str | None = None
    limit: int = 100


class QueryHandler(ABC):
    """Base query handler."""

    @abstractmethod
    def handle(self, query: Query) -> Any:
        """Handle a query."""
        pass


class GetStockHandler(QueryHandler):
    """Handler for getting stocks."""

    def __init__(self, aggregate_registry=None):
        from app.application.aggregate_registry import get_aggregate_registry
        self._registry = aggregate_registry or get_aggregate_registry()

    def handle(self, query: GetStockQuery) -> dict:
        """Handle get stock query."""
        stock = self._registry.get_stock(query.stock_code)

        if not stock:
            return {
                "query_id": query.query_id,
                "status": "not_found",
                "stock_code": query.stock_code,
            }

        return {
            "query_id": query.query_id,
            "status": "success",
            "stock": stock.to_dict(),
        }


class GetPortfolioHandler(QueryHandler):
    """Handler for getting portfolios."""

    def __init__(self, aggregate_registry=None, market_provider=None):
        from app.application.aggregate_registry import get_aggregate_registry
        self._registry = aggregate_registry or get_aggregate_registry()
        self._market_provider = market_provider

    def handle(self, query: GetPortfolioQuery) -> dict:
        """Handle get portfolio query."""
        portfolio = self._registry.get_portfolio(query.portfolio_id)

        if not portfolio:
            return {
                "query_id": query.query_id,
                "status": "not_found",
                "portfolio_id": query.portfolio_id,
            }

        prices = {}
        if self._market_provider:
            for pos in portfolio._positions:
                quote = self._market_provider.get_quote(pos.stock_code)
                prices[pos.stock_code] = quote.get("price", pos.avg_price)

        snapshot = portfolio.create_snapshot(prices)

        return {
            "query_id": query.query_id,
            "status": "success",
            "portfolio": {
                "id": str(portfolio.id),
                "cash": portfolio.cash,
                "total_market_value": snapshot.total_market_value,
                "total_assets": snapshot.total_assets,
                "pnl": snapshot.total_pnl,
                "pnl_pct": snapshot.pnl_pct,
                "position_count": portfolio.position_count,
                "positions": [
                    {
                        "stock_code": p.stock_code,
                        "quantity": p.quantity,
                        "avg_price": p.avg_price,
                        "market_value": p.market_value,
                    }
                    for p in snapshot.positions
                ],
            },
        }


class GetOrdersHandler(QueryHandler):
    """Handler for getting orders."""

    def __init__(self, aggregate_registry=None):
        from app.application.aggregate_registry import get_aggregate_registry
        self._registry = aggregate_registry or get_aggregate_registry()

    def handle(self, query: GetOrdersQuery) -> dict:
        """Handle get orders query."""
        session = self._registry.get_trading_session(query.portfolio_id)

        if not session:
            return {
                "query_id": query.query_id,
                "status": "not_found",
                "orders": [],
            }

        from app.domain.aggregates.trading_session_aggregate import OrderStatus

        orders = session.get_orders(
            status=OrderStatus(query.status) if query.status else None
        )

        return {
            "query_id": query.query_id,
            "status": "success",
            "orders": [
                {
                    "stock_code": o.stock_code,
                    "side": o.side.value,
                    "quantity": o.quantity,
                    "filled": o.filled_quantity,
                    "status": o.status.value,
                    "created_at": o.created_at.isoformat(),
                }
                for o in orders
            ],
        }


class GetSignalsHandler(QueryHandler):
    """Handler for getting signals."""

    def __init__(self, aggregate_registry=None):
        from app.application.aggregate_registry import get_aggregate_registry
        self._registry = aggregate_registry or get_aggregate_registry()

    def handle(self, query: GetSignalsQuery) -> dict:
        """Handle get signals query."""
        stock = self._registry.get_stock(query.stock_code)

        if not stock:
            return {
                "query_id": query.query_id,
                "status": "not_found",
                "signals": [],
            }

        signals = stock.get_signals(active_only=query.active_only)

        return {
            "query_id": query.query_id,
            "status": "success",
            "signals": [
                {
                    "stock_code": s.stock_code,
                    "signal_type": s.signal_type.value,
                    "confidence": s.confidence,
                    "reason": s.reason,
                    "created_at": s.created_at.isoformat(),
                }
                for s in signals
            ],
        }


class GetEventHistoryHandler(QueryHandler):
    """Handler for getting event history."""

    def __init__(self, event_publisher=None):
        from app.application.event_publisher import get_event_publisher
        self._publisher = event_publisher or get_event_publisher()

    def handle(self, query: GetEventHistoryQuery) -> dict:
        """Handle get event history query."""
        events = self._publisher.get_event_history(
            aggregate_id=query.aggregate_id,
            limit=query.limit,
        )

        return {
            "query_id": query.query_id,
            "status": "success",
            "count": len(events),
            "events": events,
        }


__all__ = [
    "Query",
    "GetStockQuery",
    "GetPortfolioQuery",
    "GetOrdersQuery",
    "GetSignalsQuery",
    "GetMarketDataQuery",
    "GetEventHistoryQuery",
    "QueryHandler",
    "GetStockHandler",
    "GetPortfolioHandler",
    "GetOrdersHandler",
    "GetSignalsHandler",
    "GetEventHistoryHandler",
]
