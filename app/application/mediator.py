from __future__ import annotations

"""CQRS Mediator - Dispatches commands and queries.

Mediator pattern for CQRS command/query dispatching.
"""


from collections.abc import Callable
from typing import Any

from app.application.commands import (
    Command,
    CommandHandler,
    CreateStockCommand,
    CreateStockHandler,
    GenerateSignalCommand,
    GenerateSignalHandler,
    ScreenStocksCommand,
    ScreenStocksHandler,
    SubmitOrderCommand,
    SubmitOrderHandler,
    UpdatePositionCommand,
    UpdatePositionHandler,
)
from app.application.queries import (
    GetEventHistoryHandler,
    GetEventHistoryQuery,
    GetOrdersHandler,
    GetOrdersQuery,
    GetPortfolioHandler,
    GetPortfolioQuery,
    GetSignalsHandler,
    GetSignalsQuery,
    GetStockHandler,
    GetStockQuery,
    Query,
    QueryHandler,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class MediatorError(Exception):
    """Mediator error."""
    pass


class HandlerNotFoundError(MediatorError):
    """Handler not found."""
    pass


class Mediator:
    """CQRS Mediator for dispatching commands and queries."""

    def __init__(self):
        self._command_handlers: dict[type, CommandHandler] = {}
        self._query_handlers: dict[type, QueryHandler] = {}
        self._middleware: list[Callable] = []

        self._register_default_handlers()
        logger.info("Mediator initialized")

    def _register_default_handlers(self) -> None:
        """Register default handlers."""
        self.register_command(CreateStockCommand, CreateStockHandler())
        self.register_command(UpdatePositionCommand, UpdatePositionHandler())
        self.register_command(SubmitOrderCommand, SubmitOrderHandler())
        self.register_command(ScreenStocksCommand, ScreenStocksHandler())
        self.register_command(GenerateSignalCommand, GenerateSignalHandler())

        self.register_query(GetStockQuery, GetStockHandler())
        self.register_query(GetPortfolioQuery, GetPortfolioHandler())
        self.register_query(GetOrdersQuery, GetOrdersHandler())
        self.register_query(GetSignalsQuery, GetSignalsHandler())
        self.register_query(GetEventHistoryQuery, GetEventHistoryHandler())

    def register_command(
        self,
        command_type: type,
        handler: CommandHandler
    ) -> Mediator:
        """Register a command handler."""
        self._command_handlers[command_type] = handler
        return self

    def register_query(
        self,
        query_type: type,
        handler: QueryHandler
    ) -> Mediator:
        """Register a query handler."""
        self._query_handlers[query_type] = handler
        return self

    def add_middleware(self, middleware: Callable) -> Mediator:
        """Add middleware."""
        self._middleware.append(middleware)
        return self

    def send(self, command: Command) -> Any:
        """Send a command."""
        logger.debug(f"Sending command: {command.__class__.__name__}")

        for middleware in self._middleware:
            middleware(command)

        command_type = type(command)
        handler = self._command_handlers.get(command_type)

        if not handler:
            raise HandlerNotFoundError(
                f"No handler for command: {command_type.__name__}"
            )

        return handler.handle(command)

    def fetch(self, query: Query) -> Any:
        """Fetch using query."""
        logger.debug(f"Fetching query: {query.__class__.__name__}")

        for middleware in self._middleware:
            middleware(query)

        query_type = type(query)
        handler = self._query_handlers.get(query_type)

        if not handler:
            raise HandlerNotFoundError(
                f"No handler for query: {query_type.__name__}"
            )

        return handler.handle(query)

    def send_async(self, command: Command) -> Any:
        """Send command asynchronously (for future async support)."""
        return self.send(command)

    def fetch_async(self, query: Query) -> Any:
        """Fetch query asynchronously."""
        return self.fetch(query)


_global_mediator: Mediator | None = None


def get_mediator() -> Mediator:
    """Get global mediator."""
    global _global_mediator
    if _global_mediator is None:
        _global_mediator = Mediator()
    return _global_mediator


def send(command: Command) -> Any:
    """Convenience function to send command."""
    return get_mediator().send(command)


def fetch(query: Query) -> Any:
    """Convenience function to fetch query."""
    return get_mediator().fetch(query)


def create_stock(stock_code: str, name: str, market: str = "A") -> dict:
    """Create stock command."""
    from app.application.commands import CreateStockCommand
    return send(CreateStockCommand(
        stock_code=stock_code,
        name=name,
        market=market,
    ))


def get_stock(stock_code: str) -> dict:
    """Get stock query."""
    from app.application.queries import GetStockQuery
    return fetch(GetStockQuery(stock_code=stock_code))


def get_portfolio(portfolio_id: str) -> dict:
    """Get portfolio query."""
    from app.application.queries import GetPortfolioQuery
    return fetch(GetPortfolioQuery(portfolio_id=portfolio_id))


def screen_stocks(criteria: dict) -> dict:
    """Screen stocks command."""
    from app.application.commands import ScreenStocksCommand
    return send(ScreenStocksCommand(criteria=criteria))


def generate_signal(stock_code: str, indicators: dict = None) -> dict:
    """Generate signal command."""
    from app.application.commands import GenerateSignalCommand
    return send(GenerateSignalCommand(
        stock_code=stock_code,
        indicators=indicators or {},
    ))


def get_event_history(aggregate_id: str = None, limit: int = 100) -> dict:
    """Get event history query."""
    from app.application.queries import GetEventHistoryQuery
    return fetch(GetEventHistoryQuery(
        aggregate_id=aggregate_id,
        limit=limit,
    ))


__all__ = [
    "Mediator",
    "MediatorError",
    "HandlerNotFoundError",
    "get_mediator",
    "send",
    "fetch",
    "create_stock",
    "get_stock",
    "get_portfolio",
    "screen_stocks",
    "generate_signal",
    "get_event_history",
]
