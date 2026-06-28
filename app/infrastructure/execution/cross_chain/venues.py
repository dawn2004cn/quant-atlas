"""Concrete execution venue implementations."""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import datetime
from typing import Any

from .execution_venue import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionVenue,
    OrderSide,
    VenueStatus,
)

logger = logging.getLogger(__name__)


class RedisShadowVenue(ExecutionVenue):
    """Redis-based shadow/paper trading venue.

    Executes trades in a shadow ledger for testing and strategy validation.
    No real market interaction - all fills are simulated.
    """

    def __init__(
        self,
        *,
        redis_client: Any | None = None,
        slippage_bps: float = 5.0,
        commission_bps: float = 3.0,
    ):
        super().__init__(venue_id="redis_shadow", priority=50, max_retries=3)
        self._redis = redis_client
        self._slippage_bps = slippage_bps
        self._commission_bps = commission_bps
        self._orders: dict[str, dict[str, Any]] = {}

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute shadow trade with simulated fills."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Shadow venue: use last close when limit price missing
            base_price = request.price
            if not base_price or base_price <= 0:
                base_price = self._resolve_reference_price(request.symbol)
            if not base_price or base_price <= 0:
                base_price = 100.0
                logger.warning(
                    "shadow venue using fallback price=100 for %s (no quote)",
                    request.symbol,
                )
            slippage = base_price * (self._slippage_bps / 10000)

            if request.side == OrderSide.BUY:
                fill_price = base_price + slippage
            else:
                fill_price = base_price - slippage

            # Calculate commission
            notional = request.quantity * fill_price
            commission = notional * (self._commission_bps / 10000)

            # Generate order ID
            order_id = f"shadow-{uuid.uuid4().hex[:12]}"

            # Store order
            self._orders[order_id] = {
                "order_id": order_id,
                "symbol": request.symbol,
                "side": request.side.value,
                "quantity": request.quantity,
                "fill_price": fill_price,
                "commission": commission,
                "status": "filled",
                "timestamp": datetime.now().isoformat(),
            }

            # Persist to Redis if available
            if self._redis:
                try:
                    import json
                    key = f"shadow:order:{order_id}"
                    self._redis.setex(key, 86400, json.dumps(self._orders[order_id]))
                except Exception as exc:
                    logger.debug("shadow redis persist skipped: %s", exc)

            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self._record_success(latency_ms)

            return ExecutionResult(
                success=True,
                venue_id=self.venue_id,
                order_id=order_id,
                filled_quantity=request.quantity,
                fill_price=fill_price,
                commission=commission,
                latency_ms=latency_ms,
                metadata={"shadow": True, "slippage_bps": self._slippage_bps},
            )

        except Exception as exc:
            self._record_failure(str(exc))
            return ExecutionResult(
                success=False,
                venue_id=self.venue_id,
                error=str(exc),
            )

    async def health_check(self) -> VenueStatus:
        """Shadow venue is always healthy (no external dependencies)."""
        if self._redis:
            try:
                self._redis.ping()
                self._status = VenueStatus.HEALTHY
            except Exception:
                self._status = VenueStatus.DEGRADED
        else:
            self._status = VenueStatus.HEALTHY
        return self._status

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel shadow order."""
        if order_id in self._orders:
            self._orders[order_id]["status"] = "cancelled"
            return True
        return False

    async def get_order_status(self, order_id: str) -> dict[str, Any]:
        """Get shadow order status."""
        return self._orders.get(order_id, {"order_id": order_id, "status": "not_found"})


class MockQMTVenue(ExecutionVenue):
    """Mock QMT (Quant Master Terminal) venue for testing.

    Simulates QMT execution with realistic latency and occasional failures.
    """

    def __init__(
        self,
        *,
        failure_rate: float = 0.05,
        latency_range: tuple[float, float] = (50.0, 200.0),
    ):
        super().__init__(venue_id="mock_qmt", priority=10, max_retries=3)
        self._failure_rate = failure_rate
        self._latency_range = latency_range
        self._orders: dict[str, dict[str, Any]] = {}

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Simulate QMT execution with realistic behavior."""
        # Simulate network latency
        latency_ms = random.uniform(*self._latency_range)
        await asyncio.sleep(latency_ms / 1000)

        # Simulate random failures
        if random.random() < self._failure_rate:
            error = random.choice([
                "QMT connection timeout",
                "Order rejected by risk control",
                "Insufficient buying power",
                "Market data feed interrupted",
            ])
            self._record_failure(error)
            return ExecutionResult(
                success=False,
                venue_id=self.venue_id,
                error=error,
                latency_ms=latency_ms,
            )

        # Simulate successful fill
        order_id = f"qmt-{uuid.uuid4().hex[:12]}"
        fill_price = request.price or 100.0
        commission = request.quantity * fill_price * 0.0003  # 3bps

        self._orders[order_id] = {
            "order_id": order_id,
            "symbol": request.symbol,
            "side": request.side.value,
            "quantity": request.quantity,
            "fill_price": fill_price,
            "status": "filled",
        }

        self._record_success(latency_ms)

        return ExecutionResult(
            success=True,
            venue_id=self.venue_id,
            order_id=order_id,
            filled_quantity=request.quantity,
            fill_price=fill_price,
            commission=commission,
            latency_ms=latency_ms,
            metadata={"qmt_session": "mock-session-001"},
        )

    async def health_check(self) -> VenueStatus:
        """Simulate QMT health check."""
        # Simulate occasional health check failures
        if random.random() < 0.02:
            self._status = VenueStatus.DEGRADED
        else:
            self._status = VenueStatus.HEALTHY
        return self._status


class DeFiBridgeVenue(ExecutionVenue):
    """DeFi bridge venue for on-chain execution (mock implementation).

    Simulates DEX aggregator execution with gas costs and slippage.
    """

    def __init__(
        self,
        *,
        gas_cost_usd: float = 5.0,
        slippage_bps: float = 30.0,
    ):
        super().__init__(venue_id="defi_bridge", priority=80, max_retries=2)
        self._gas_cost_usd = gas_cost_usd
        self._slippage_bps = slippage_bps
        self._orders: dict[str, dict[str, Any]] = {}

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Simulate DeFi execution with gas costs."""
        start_time = asyncio.get_event_loop().time()

        # Simulate blockchain latency (slower than CEX)
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # Calculate fill with higher slippage
        base_price = request.price or 100.0
        slippage = base_price * (self._slippage_bps / 10000)

        if request.side == OrderSide.BUY:
            fill_price = base_price + slippage
        else:
            fill_price = base_price - slippage

        order_id = f"defi-{uuid.uuid4().hex[:12]}"
        tx_hash = f"0x{uuid.uuid4().hex}"

        self._orders[order_id] = {
            "order_id": order_id,
            "tx_hash": tx_hash,
            "symbol": request.symbol,
            "side": request.side.value,
            "quantity": request.quantity,
            "fill_price": fill_price,
            "gas_cost_usd": self._gas_cost_usd,
            "status": "confirmed",
        }

        latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        self._record_success(latency_ms)

        return ExecutionResult(
            success=True,
            venue_id=self.venue_id,
            order_id=order_id,
            filled_quantity=request.quantity,
            fill_price=fill_price,
            commission=self._gas_cost_usd,
            latency_ms=latency_ms,
            metadata={
                "tx_hash": tx_hash,
                "gas_cost_usd": self._gas_cost_usd,
                "slippage_bps": self._slippage_bps,
                "chain": "ethereum",
            },
        )

    async def health_check(self) -> VenueStatus:
        """Simulate DeFi health check (depends on gas prices)."""
        # Simulate occasional high gas price degradation
        if random.random() < 0.1:
            self._status = VenueStatus.DEGRADED
        else:
            self._status = VenueStatus.HEALTHY
        return self._status


__all__ = [
    "RedisShadowVenue",
    "MockQMTVenue",
    "DeFiBridgeVenue",
]
