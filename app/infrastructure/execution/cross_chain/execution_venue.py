"""Execution Venue — abstract base for trade execution venues."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class VenueStatus(str, Enum):
    """Venue health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class ExecutionRequest:
    """Trade execution request."""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    price: float | None = None
    stop_price: float | None = None
    venue_preference: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    idempotency_key: str = ""


@dataclass
class ExecutionResult:
    """Trade execution result."""
    success: bool
    venue_id: str
    order_id: str = ""
    filled_quantity: float = 0.0
    fill_price: float = 0.0
    commission: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: str = ""
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "venue_id": self.venue_id,
            "order_id": self.order_id,
            "filled_quantity": self.filled_quantity,
            "fill_price": self.fill_price,
            "commission": self.commission,
            "timestamp": self.timestamp,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


class ExecutionVenue(ABC):
    """Abstract base class for trade execution venues.
    
    Each venue represents a different execution path:
    - QMT venue: Direct market access via QMT terminal
    - Redis shadow venue: Paper trading / shadow execution
    - DeFi bridge: On-chain execution via DEX aggregators
    - Broker API: Traditional broker API execution
    """

    def __init__(self, venue_id: str, *, priority: int = 100, max_retries: int = 3):
        self._venue_id = venue_id
        self._priority = priority
        self._max_retries = max_retries
        self._status = VenueStatus.HEALTHY
        self._last_health_check: datetime | None = None
        self._consecutive_failures = 0
        self._total_executions = 0
        self._total_failures = 0

    @property
    def venue_id(self) -> str:
        return self._venue_id

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def status(self) -> VenueStatus:
        return self._status

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "venue_id": self._venue_id,
            "status": self._status.value,
            "priority": self._priority,
            "total_executions": self._total_executions,
            "total_failures": self._total_failures,
            "consecutive_failures": self._consecutive_failures,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
        }

    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a trade order.
        
        Args:
            request: The execution request
            
        Returns:
            ExecutionResult with fill details or error
        """
        pass

    @abstractmethod
    async def health_check(self) -> VenueStatus:
        """Check venue health.
        
        Returns:
            Current VenueStatus
        """
        pass

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order.
        
        Args:
            order_id: The order to cancel
            
        Returns:
            True if cancellation succeeded
        """
        return False

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get order status.
        
        Args:
            order_id: The order to query
            
        Returns:
            Order status dict
        """
        return {"order_id": order_id, "status": "unknown"}

    def _record_success(self, latency_ms: float) -> None:
        """Record a successful execution."""
        self._total_executions += 1
        self._consecutive_failures = 0
        self._last_health_check = datetime.now()
        if self._status != VenueStatus.HEALTHY:
            self._status = VenueStatus.HEALTHY
            logger.info("venue %s recovered to HEALTHY", self._venue_id)

    def _record_failure(self, error: str) -> None:
        """Record a failed execution."""
        self._total_executions += 1
        self._total_failures += 1
        self._consecutive_failures += 1
        self._last_health_check = datetime.now()
        
        if self._consecutive_failures >= self._max_retries:
            self._status = VenueStatus.UNHEALTHY
            logger.warning("venue %s marked UNHEALTHY after %d failures", 
                          self._venue_id, self._consecutive_failures)
        elif self._consecutive_failures >= 2:
            self._status = VenueStatus.DEGRADED
            logger.warning("venue %s marked DEGRADED after %d failures",
                          self._venue_id, self._consecutive_failures)

    def reset_status(self) -> None:
        """Manually reset venue status to HEALTHY."""
        self._status = VenueStatus.HEALTHY
        self._consecutive_failures = 0
        logger.info("venue %s manually reset to HEALTHY", self._venue_id)


__all__ = [
    "ExecutionVenue",
    "ExecutionRequest",
    "ExecutionResult",
    "VenueStatus",
    "OrderSide",
    "OrderType",
]
