"""Domain aggregates - aggregate roots enforcing invariants.

This module exposes all aggregate roots for the domain layer.
Aggregates encapsulate entities and enforce business invariants.
"""

from app.domain.aggregates.stock_aggregate import (
    StockAggregate,
    StockAggregateError,
    InvalidStockCodeError,
    DuplicateSignalError,
    StockAggregateFactory,
)
from app.domain.aggregates.portfolio_aggregate import (
    PortfolioAggregate,
    PortfolioAggregateError,
    PositionLimitExceededError,
    InsufficientCapitalError,
    InvalidPositionError,
    PositionEntity,
)
from app.domain.aggregates.trading_session_aggregate import (
    TradingSessionAggregate,
    TradingSessionFactory,
    TradingSessionError,
    InvalidOrderError,
    OrderNotFoundError,
    InvalidTransitionError,
    OrderEntity,
    ExecutionEntity,
    OrderStatus,
    OrderSide,
    OrderType,
)

__all__ = [
    # Stock Aggregate
    "StockAggregate",
    "StockAggregateError",
    "InvalidStockCodeError",
    "DuplicateSignalError",
    "StockAggregateFactory",
    # Portfolio Aggregate
    "PortfolioAggregate",
    "PortfolioAggregateError",
    "PositionLimitExceededError",
    "InsufficientCapitalError",
    "InvalidPositionError",
    "PositionEntity",
    # Trading Session Aggregate
    "TradingSessionAggregate",
    "TradingSessionFactory",
    "TradingSessionError",
    "InvalidOrderError",
    "OrderNotFoundError",
    "InvalidTransitionError",
    "OrderEntity",
    "ExecutionEntity",
    "OrderStatus",
    "OrderSide",
    "OrderType",
]
