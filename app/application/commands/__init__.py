from __future__ import annotations
"""CQRS Command Handlers.

Commands for modifying domain state.
"""


import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Command:
    """Base command."""
    command_id: str = ""
    created_at: datetime = None
    
    def __post_init__(self):
        if not self.command_id:
            self.command_id = f"cmd_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        if not self.created_at:
            self.created_at = datetime.now()


@dataclass
class CreateStockCommand(Command):
    """Create a new stock."""
    stock_code: str = ""
    name: str = ""
    market: str = "A"


@dataclass
class UpdatePositionCommand(Command):
    """Update a position."""
    portfolio_id: str = ""
    stock_code: str = ""
    quantity: float = 0.0
    price: float = 0.0
    action: str = "add"  # add, reduce, close


@dataclass
class SubmitOrderCommand(Command):
    """Submit an order."""
    portfolio_id: str = ""
    stock_code: str = ""
    side: str = "buy"  # buy, sell
    order_type: str = "market"  # market, limit, stop
    quantity: float = 0.0
    price: Optional[float] = None


@dataclass
class CancelOrderCommand(Command):
    """Cancel an order."""
    order_id: str = ""


@dataclass
class ScreenStocksCommand(Command):
    """Screen stocks with criteria."""
    criteria: dict = None
    
    def __post_init__(self):
        super().__post_init__()
        if not self.criteria:
            self.criteria = {}


@dataclass
class GenerateSignalCommand(Command):
    """Generate a signal for stock."""
    stock_code: str = ""
    indicators: dict = None
    
    def __post_init__(self):
        super().__post_init__()
        if not self.indicators:
            self.indicators = {}


class CommandHandler(ABC):
    """Base command handler."""
    
    @abstractmethod
    def handle(self, command: Command) -> Any:
        """Handle a command."""
        pass


class CreateStockHandler(CommandHandler):
    """Handler for creating stocks."""
    
    def __init__(self, aggregate_registry=None):
        from app.application.aggregate_registry import get_aggregate_registry
        self._registry = aggregate_registry or get_aggregate_registry()
    
    def handle(self, command: CreateStockCommand) -> dict:
        """Handle create stock command."""
        stock = self._registry.create_stock(
            command.stock_code,
            command.name,
            command.market
        )
        
        from app.application.event_publisher import emit_stock_created
        emit_stock_created(command.stock_code, command.name, command.market)
        
        logger.info(f"Created stock: {command.stock_code}")
        
        return {
            "command_id": command.command_id,
            "stock_code": command.stock_code,
            "status": "created",
            "aggregate_id": str(stock.id),
        }


class UpdatePositionHandler(CommandHandler):
    """Handler for updating positions."""
    
    def __init__(self, aggregate_registry=None):
        from app.application.aggregate_registry import get_aggregate_registry
        self._registry = aggregate_registry or get_aggregate_registry()
    
    def handle(self, command: UpdatePositionCommand) -> dict:
        """Handle update position command."""
        portfolio = self._registry.get_portfolio(command.portfolio_id)
        
        if not portfolio:
            return {
                "command_id": command.command_id,
                "status": "error",
                "message": f"Portfolio not found: {command.portfolio_id}",
            }
        
        if command.action == "add":
            portfolio.add_position(
                command.stock_code,
                command.quantity,
                command.price,
            )
            from app.application.event_publisher import emit_position_opened
            emit_position_opened(
                command.stock_code,
                command.quantity,
                command.price
            )
        elif command.action == "reduce":
            portfolio.reduce_position(
                command.stock_code,
                command.quantity,
                command.price
            )
        elif command.action == "close":
            portfolio.close_position(
                command.stock_code,
                command.price
            )
            from app.application.event_publisher import emit_position_closed
            emit_position_closed(
                command.stock_code,
                command.quantity,
                0.0
            )
        
        logger.info(f"Updated position: {command.stock_code}")
        
        return {
            "command_id": command.command_id,
            "stock_code": command.stock_code,
            "status": "updated",
        }


class SubmitOrderHandler(CommandHandler):
    """Handler for submitting orders."""
    
    def __init__(self, aggregate_registry=None):
        from app.application.aggregate_registry import get_aggregate_registry
        self._registry = aggregate_registry or get_aggregate_registry()
    
    def handle(self, command: SubmitOrderCommand) -> dict:
        """Handle submit order command."""
        session = self._registry.get_trading_session(command.portfolio_id)
        
        if not session:
            session = self._registry.create_trading_session(command.portfolio_id)
        
        from app.domain.aggregates.trading_session_aggregate import OrderSide, OrderType
        
        side = OrderSide.BUY if command.side == "buy" else OrderSide.SELL
        order_type = getattr(OrderType, command.order_type.upper(), OrderType.MARKET)
        
        order = session.create_order(
            command.stock_code,
            side,
            order_type,
            command.quantity,
            command.price,
        )
        
        session.submit_order(str(len(session._orders)))
        
        from app.application.event_publisher import emit_order_submitted
        emit_order_submitted(
            str(len(session._orders)),
            command.stock_code,
            command.side,
            command.quantity,
        )
        
        logger.info(f"Submitted order: {command.stock_code}")
        
        return {
            "command_id": command.command_id,
            "order_id": str(len(session._orders)),
            "status": "submitted",
        }


class ScreenStocksHandler(CommandHandler):
    """Handler for screening stocks."""
    
    def __init__(self, market_provider=None):
        self._market_provider = market_provider
    
    def handle(self, command: ScreenStocksCommand) -> dict:
        """Handle screen stocks command."""
        if not self._market_provider:
            return {
                "command_id": command.command_id,
                "status": "error",
                "message": "Market provider not available",
            }
        
        from app.application.domain_facade import get_domain_facade
        facade = get_domain_facade()
        
        all_stocks = self._market_provider.list_stocks(market="A")
        results = facade.screen_stocks(all_stocks, command.criteria)
        
        logger.info(f"Screened stocks: {len(results)} results")
        
        return {
            "command_id": command.command_id,
            "status": "success",
            "count": len(results),
            "results": results,
        }


class GenerateSignalHandler(CommandHandler):
    """Handler for generating signals."""
    
    def __init__(self, market_provider=None):
        self._market_provider = market_provider
    
    def handle(self, command: GenerateSignalCommand) -> dict:
        """Handle generate signal command."""
        indicators = command.indicators
        
        if not indicators and self._market_provider:
            indicators = self._market_provider.get_indicators(command.stock_code)
        
        from app.application.domain_facade import get_domain_facade
        facade = get_domain_facade()
        
        signal = facade.generate_signal(command.stock_code, indicators)
        
        from app.application.event_publisher import emit_signal_generated
        emit_signal_generated(
            command.stock_code,
            signal["signal_type"],
            signal["confidence"],
            "domain_service",
        )
        
        logger.info(f"Generated signal: {command.stock_code}")
        
        return {
            "command_id": command.command_id,
            "status": "success",
            "signal": signal,
        }


__all__ = [
    "Command",
    "CreateStockCommand",
    "UpdatePositionCommand",
    "SubmitOrderCommand",
    "CancelOrderCommand",
    "ScreenStocksCommand",
    "GenerateSignalCommand",
    "CommandHandler",
    "CreateStockHandler",
    "UpdatePositionHandler",
    "SubmitOrderHandler",
    "ScreenStocksHandler",
    "GenerateSignalHandler",
]