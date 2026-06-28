"""Execution Driver - 解耦交易执行逻辑与业务逻辑。

提供两种执行模式:
1. RedisStreamExecutor: 基于 Redis Stream 的异步执行
2. GrpcExecutor: 基于 gRPC 的远程执行 (预留)
"""

from .order_manager import OrderManager
from .protocol import (
    ExecutionGateway,
    OrderSide,
    OrderStatus,
    OrderType,
    TradeRequest,
    TradeResponse,
)
from .redis_executor import RedisStreamExecutor

__all__ = [
    "TradeRequest",
    "TradeResponse",
    "OrderStatus",
    "OrderSide",
    "OrderType",
    "ExecutionGateway",
    "RedisStreamExecutor",
    "OrderManager",
]
