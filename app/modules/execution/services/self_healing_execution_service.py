"""Self-Healing Execution Service — integrates CrossChainDriver with EventBus monitoring (10.0)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from app.core.event_bus import Event, get_event_bus
from app.infrastructure.execution.cross_chain import (
    CrossChainDriver,
    ExecutionRequest,
    ExecutionResult,
    OrderSide,
    OrderType,
    VenueRegistry,
    VenueStatus,
)
from app.infrastructure.execution.cross_chain.venues import (
    DeFiBridgeVenue,
    MockQMTVenue,
    RedisShadowVenue,
)

logger = logging.getLogger(__name__)


class ExecutionFailoverEvent(Event):
    """Event published when execution fails over to a different venue."""
    
    event_type = "execution_failover"
    priority = 50  # HIGH
    ttl_seconds = 3600
    
    def __init__(
        self,
        *,
        source: str = "self_healing_execution",
        symbol: str,
        original_venue: str,
        failover_venue: str,
        error: str,
        attempt: int,
    ):
        super().__init__(source=source, priority=self.priority, ttl_seconds=self.ttl_seconds)
        self.symbol = symbol
        self.original_venue = original_venue
        self.failover_venue = failover_venue
        self.error = error
        self.attempt = attempt


class ExecutionRecoveryEvent(Event):
    """Event published when a venue recovers from UNHEALTHY status."""
    
    event_type = "execution_recovery"
    priority = 30  # NORMAL
    ttl_seconds = 1800
    
    def __init__(
        self,
        *,
        source: str = "self_healing_execution",
        venue_id: str,
        previous_status: str,
        new_status: str,
    ):
        super().__init__(source=source, priority=self.priority, ttl_seconds=self.ttl_seconds)
        self.venue_id = venue_id
        self.previous_status = previous_status
        self.new_status = new_status


class SelfHealingExecutionService:
    """Self-healing execution service with automatic failover and EventBus integration.
    
    This service wraps the CrossChainDriver and provides:
    - Automatic venue registration on startup
    - EventBus integration for real-time monitoring
    - High-level order submission API
    - Execution statistics and audit trail
    """

    def __init__(
        self,
        *,
        registry: VenueRegistry | None = None,
        driver: CrossChainDriver | None = None,
        redis_client: Any | None = None,
        enable_monitoring: bool = True,
    ):
        self._registry = registry or VenueRegistry(health_check_interval=30)
        self._driver = driver or CrossChainDriver(self._registry, max_total_retries=5)
        self._redis = redis_client
        self._event_bus = get_event_bus()
        self._enable_monitoring = enable_monitoring
        self._venue_status_history: dict[str, list[dict[str, Any]]] = {}
        
        # Register default venues
        self._register_default_venues()
        
        # Start health monitoring
        if enable_monitoring:
            self._registry.start_monitoring()

    def _register_default_venues(self) -> None:
        """Register default execution venues."""
        # QMT venue (highest priority for CN market)
        qmt = MockQMTVenue(failure_rate=0.05, latency_range=(50.0, 200.0))
        self._registry.register(qmt)
        
        # Redis shadow venue (fallback for paper trading)
        shadow = RedisShadowVenue(redis_client=self._redis, slippage_bps=5.0)
        self._registry.register(shadow)
        
        # DeFi bridge venue (for crypto/cross-chain)
        defi = DeFiBridgeVenue(gas_cost_usd=5.0, slippage_bps=30.0)
        self._registry.register(defi)
        
        logger.info("registered %d default execution venues", len(self._registry.get_all_venues()))

    async def submit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        price: float | None = None,
        order_type: str = "market",
        venue_preference: list[str] | None = None,
        idempotency_key: str | None = None,
        timeout_seconds: int = 30,
    ) -> dict[str, Any]:
        """Submit an order with automatic failover.
        
        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Order quantity
            price: Limit price (for limit orders)
            order_type: "market", "limit", "stop", "stop_limit"
            venue_preference: Preferred venue IDs to try first
            idempotency_key: Optional idempotency key for safe retries
            timeout_seconds: Execution timeout per venue
            
        Returns:
            Execution result dict
        """
        # Parse order side
        try:
            order_side = OrderSide(side.lower())
        except ValueError:
            return {"ok": False, "error": f"invalid_side: {side}"}
        
        # Parse order type
        try:
            otype = OrderType(order_type.lower())
        except ValueError:
            return {"ok": False, "error": f"invalid_order_type: {order_type}"}
        
        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"order-{uuid.uuid4().hex[:16]}"
        
        # Perception-aware venue preference (10.0 Neural Resonance)
        effective_venue_preference = venue_preference or []
        if not effective_venue_preference:
            # Query perception layer for optimal venue based on recent executions
            perception_preference = self.get_perception_aware_venue_preference(symbol, side)
            if perception_preference:
                effective_venue_preference = perception_preference
                logger.debug("using perception-aware venue preference: %s", perception_preference)
        
        # Build execution request
        request = ExecutionRequest(
            symbol=symbol,
            side=order_side,
            quantity=quantity,
            order_type=otype,
            price=price,
            venue_preference=effective_venue_preference,
            idempotency_key=idempotency_key,
            timeout_seconds=timeout_seconds,
            metadata={
                "submitted_at": datetime.now().isoformat(),
                "source": "self_healing_execution_service",
                "perception_aware": bool(perception_preference) if not venue_preference else False,
            },
        )
        
        # Execute with failover
        try:
            result = await self._driver.execute(request, preferred_venues=venue_preference)
            
            # Publish failover event if execution required multiple attempts
            if not result.success and result.metadata.get("attempts", 1) > 1:
                self._publish_failover_event(symbol, result)
            
            # Publish execution result to perception layer (10.0 Neural Resonance)
            self._publish_execution_to_perception(symbol, side, result)
            
            return {
                "ok": result.success,
                "order_id": result.order_id,
                "venue_id": result.venue_id,
                "filled_quantity": result.filled_quantity,
                "fill_price": result.fill_price,
                "commission": result.commission,
                "latency_ms": result.latency_ms,
                "error": result.error if not result.success else None,
                "idempotency_key": idempotency_key,
            }
            
        except Exception as exc:
            logger.error("execution failed for %s: %s", symbol, exc)
            # Publish failure to perception layer
            self._publish_execution_failure_to_perception(symbol, side, str(exc))
            return {"ok": False, "error": str(exc), "idempotency_key": idempotency_key}

    def _publish_failover_event(self, symbol: str, result: ExecutionResult) -> None:
        """Publish execution failover event to EventBus."""
        try:
            event = ExecutionFailoverEvent(
                symbol=symbol,
                original_venue=result.metadata.get("original_venue", "unknown"),
                failover_venue=result.venue_id,
                error=result.error,
                attempt=result.metadata.get("attempts", 1),
            )
            self._event_bus.publish(event)
            logger.info("published failover event for %s", symbol)
        except Exception as exc:
            logger.debug("failed to publish failover event: %s", exc)

    def _publish_execution_to_perception(
        self,
        symbol: str,
        side: str,
        result: ExecutionResult,
    ) -> None:
        """Publish execution result to perception layer for cross-node resonance (10.0).
        
        This allows other nodes to detect execution patterns and react accordingly.
        For example, if multiple nodes are buying the same symbol, it may indicate
        a strong signal that triggers additional research or position sizing adjustments.
        """
        try:
            from app.core.mesh.perception_bridge import publish_perception
            
            if result.success:
                # Publish successful execution
                perception_text = f"execution_success:{symbol}:{side}"
                publish_perception(
                    text=perception_text,
                    metadata={
                        "type": "execution_result",
                        "symbol": symbol,
                        "side": side,
                        "venue_id": result.venue_id,
                        "fill_price": result.fill_price,
                        "filled_quantity": result.filled_quantity,
                        "latency_ms": result.latency_ms,
                        "status": "success",
                    },
                    ttl_seconds=300,
                )
                logger.debug("published execution success to perception: %s %s", symbol, side)
            else:
                # Publish failed execution
                perception_text = f"execution_failure:{symbol}:{side}"
                publish_perception(
                    text=perception_text,
                    metadata={
                        "type": "execution_result",
                        "symbol": symbol,
                        "side": side,
                        "venue_id": result.venue_id,
                        "error": result.error,
                        "status": "failure",
                    },
                    ttl_seconds=300,
                )
                logger.debug("published execution failure to perception: %s %s", symbol, side)
                
        except Exception as exc:
            logger.debug("perception layer publish skipped: %s", exc)

    def _publish_execution_failure_to_perception(
        self,
        symbol: str,
        side: str,
        error: str,
    ) -> None:
        """Publish execution exception to perception layer."""
        try:
            from app.core.mesh.perception_bridge import publish_perception
            
            perception_text = f"execution_exception:{symbol}:{side}"
            publish_perception(
                text=perception_text,
                metadata={
                    "type": "execution_result",
                    "symbol": symbol,
                    "side": side,
                    "error": error,
                    "status": "exception",
                },
                ttl_seconds=300,
            )
            logger.debug("published execution exception to perception: %s %s", symbol, side)
        except Exception as exc:
            logger.debug("perception layer publish skipped: %s", exc)

    def get_perception_aware_venue_preference(
        self,
        symbol: str,
        side: str,
    ) -> list[str]:
        """Query perception layer to determine optimal venue preference (10.0).
        
        This method checks the perception layer for recent execution signals related
        to the given symbol. If other nodes have successfully executed on a specific
        venue, we prefer that venue to leverage their proven path.
        
        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            
        Returns:
            List of preferred venue IDs, ordered by preference
        """
        try:
            from app.core.mesh.perception_layer import get_perception_layer
            
            layer = get_perception_layer()
            if not layer:
                return []
            
            # Query for recent execution signals
            query_text = f"execution_success:{symbol}"
            results = layer.query(
                text=query_text,
                top_k=10,
                min_similarity=0.6,
            )
            
            if not results:
                return []
            
            # Count venue successes
            venue_scores: dict[str, dict[str, Any]] = {}
            for r in results:
                metadata = r.get("vector", {}).get("metadata", {})
                if metadata.get("type") != "execution_result":
                    continue
                if metadata.get("status") != "success":
                    continue
                if metadata.get("side") != side:
                    continue
                    
                venue_id = metadata.get("venue_id", "")
                if not venue_id:
                    continue
                
                if venue_id not in venue_scores:
                    venue_scores[venue_id] = {
                        "count": 0,
                        "avg_latency": 0.0,
                        "total_latency": 0.0,
                    }
                
                venue_scores[venue_id]["count"] += 1
                latency = metadata.get("latency_ms", 0.0)
                venue_scores[venue_id]["total_latency"] += latency
            
            # Calculate average latency and sort by score
            for venue_id, stats in venue_scores.items():
                if stats["count"] > 0:
                    stats["avg_latency"] = stats["total_latency"] / stats["count"]
            
            # Sort by: (1) success count desc, (2) avg latency asc
            sorted_venues = sorted(
                venue_scores.items(),
                key=lambda x: (-x[1]["count"], x[1]["avg_latency"]),
            )
            
            preferred = [v[0] for v in sorted_venues]
            
            if preferred:
                logger.info(
                    "perception-aware routing for %s %s: %s",
                    symbol, side, preferred,
                )
            
            return preferred
            
        except Exception as exc:
            logger.debug("perception-aware routing skipped: %s", exc)
            return []

    def get_manifest(self) -> dict[str, Any]:
        """Get service status manifest."""
        return {
            "ok": True,
            "monitoring_enabled": self._enable_monitoring,
            "driver": self._driver.get_manifest(),
        }

    def get_execution_log(
        self,
        *,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get execution history."""
        return self._driver.get_execution_log(symbol=symbol, limit=limit)

    def get_venue_stats(self) -> dict[str, Any]:
        """Get venue statistics."""
        venues = self._registry.get_all_venues()
        return {
            "ok": True,
            "venues": [v.stats for v in venues],
            "total": len(venues),
            "healthy": sum(1 for v in venues if v.status == VenueStatus.HEALTHY),
            "degraded": sum(1 for v in venues if v.status == VenueStatus.DEGRADED),
            "unhealthy": sum(1 for v in venues if v.status == VenueStatus.UNHEALTHY),
        }

    def reset_venue(self, venue_id: str) -> dict[str, Any]:
        """Manually reset a venue to HEALTHY status."""
        venue = self._registry.get_venue(venue_id)
        if not venue:
            return {"ok": False, "error": f"venue_not_found: {venue_id}"}
        
        previous_status = venue.status.value
        venue.reset_status()
        
        # Publish recovery event
        try:
            event = ExecutionRecoveryEvent(
                venue_id=venue_id,
                previous_status=previous_status,
                new_status="healthy",
            )
            self._event_bus.publish(event)
        except Exception as exc:
            logger.debug("failed to publish recovery event: %s", exc)
        
        return {"ok": True, "venue_id": venue_id, "status": "healthy"}

    async def health_check_all(self) -> dict[str, Any]:
        """Run health checks on all venues."""
        results = await self._registry.check_all_health()
        return {
            "ok": True,
            "results": {k: v.value for k, v in results.items()},
        }

    def stop(self) -> None:
        """Stop the service and cleanup resources."""
        if self._enable_monitoring:
            self._registry.stop_monitoring()
        logger.info("self-healing execution service stopped")


# Global instance
_service: SelfHealingExecutionService | None = None


def get_self_healing_execution_service() -> SelfHealingExecutionService | None:
    """Get the global SelfHealingExecutionService instance."""
    return _service


def configure_self_healing_execution_service(
    service: SelfHealingExecutionService | None,
) -> None:
    """Configure the global SelfHealingExecutionService instance."""
    global _service
    _service = service


__all__ = [
    "SelfHealingExecutionService",
    "ExecutionFailoverEvent",
    "ExecutionRecoveryEvent",
    "get_self_healing_execution_service",
    "configure_self_healing_execution_service",
]
