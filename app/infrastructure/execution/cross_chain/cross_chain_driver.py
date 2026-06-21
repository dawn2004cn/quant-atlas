"""Cross-Chain Driver — self-healing execution router with automatic failover."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from .execution_venue import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionVenue,
    VenueStatus,
)
from .venue_registry import VenueRegistry

logger = logging.getLogger(__name__)


class CrossChainDriver:
    """Self-healing execution router with automatic failover.
    
    Features:
    - Automatic venue selection by priority and health
    - Transparent failover on execution failure
    - Idempotency key support for safe retries
    - Execution tracing and audit trail
    - Cross-venue arbitrage detection
    
    Usage:
        driver = CrossChainDriver(registry)
        result = await driver.execute(request)
    """

    def __init__(
        self,
        registry: VenueRegistry,
        *,
        max_total_retries: int = 5,
        enable_tracing: bool = True,
    ):
        self._registry = registry
        self._max_total_retries = max_total_retries
        self._enable_tracing = enable_tracing
        self._execution_log: list[dict[str, Any]] = []
        self._idempotency_cache: dict[str, ExecutionResult] = {}

    async def execute(
        self,
        request: ExecutionRequest,
        *,
        preferred_venues: list[str] | None = None,
    ) -> ExecutionResult:
        """Execute a trade with automatic failover.
        
        Tries venues in priority order, failing over to the next venue
        if execution fails. Supports idempotency keys for safe retries.
        
        Args:
            request: The execution request
            preferred_venues: Optional list of venue IDs to try first
            
        Returns:
            ExecutionResult from the first successful venue, or last failure
        """
        # Check idempotency cache
        if request.idempotency_key and request.idempotency_key in self._idempotency_cache:
            logger.debug("returning cached result for idempotency_key=%s", 
                        request.idempotency_key)
            return self._idempotency_cache[request.idempotency_key]

        # Merge venue preferences
        all_preferred = list(request.venue_preference)
        if preferred_venues:
            all_preferred.extend(preferred_venues)
        all_preferred = list(dict.fromkeys(all_preferred))  # dedupe

        # Get venues in priority order
        venues = self._registry.get_healthy_venues(preferred=all_preferred or None)
        
        if not venues:
            return ExecutionResult(
                success=False,
                venue_id="none",
                error="no healthy execution venues available",
            )

        # Trace execution
        trace_id = f"exec-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        trace: list[dict[str, Any]] = []

        last_result: ExecutionResult | None = None
        attempts = 0

        for venue in venues:
            if attempts >= self._max_total_retries:
                logger.warning("max retries (%d) reached for %s", 
                             self._max_total_retries, request.symbol)
                break

            attempts += 1
            start_time = time.monotonic()

            try:
                logger.info("attempting execution on venue %s (attempt %d)", 
                           venue.venue_id, attempts)

                result = await asyncio.wait_for(
                    venue.execute(request),
                    timeout=request.timeout_seconds,
                )

                latency_ms = (time.monotonic() - start_time) * 1000
                result.latency_ms = latency_ms

                trace.append({
                    "venue_id": venue.venue_id,
                    "attempt": attempts,
                    "success": result.success,
                    "latency_ms": latency_ms,
                    "error": result.error if not result.success else None,
                })

                if result.success:
                    # Cache idempotency result
                    if request.idempotency_key:
                        self._idempotency_cache[request.idempotency_key] = result
                        # Limit cache size
                        if len(self._idempotency_cache) > 1000:
                            oldest_keys = list(self._idempotency_cache.keys())[:500]
                            for k in oldest_keys:
                                del self._idempotency_cache[k]

                    # Record execution trace
                    if self._enable_tracing:
                        self._execution_log.append({
                            "trace_id": trace_id,
                            "symbol": request.symbol,
                            "side": request.side.value,
                            "quantity": request.quantity,
                            "result": result.to_dict(),
                            "trace": trace,
                            "timestamp": datetime.now().isoformat(),
                        })
                        # Limit log size
                        if len(self._execution_log) > 10000:
                            self._execution_log = self._execution_log[-5000:]

                    logger.info("execution succeeded on venue %s (latency=%.1fms)", 
                               venue.venue_id, latency_ms)
                    return result

                # Execution failed, try next venue
                logger.warning("execution failed on venue %s: %s", 
                             venue.venue_id, result.error)
                last_result = result

            except asyncio.TimeoutError:
                latency_ms = (time.monotonic() - start_time) * 1000
                trace.append({
                    "venue_id": venue.venue_id,
                    "attempt": attempts,
                    "success": False,
                    "latency_ms": latency_ms,
                    "error": "timeout",
                })
                logger.warning("execution timeout on venue %s (%.1fms)", 
                             venue.venue_id, latency_ms)
                last_result = ExecutionResult(
                    success=False,
                    venue_id=venue.venue_id,
                    error=f"execution timeout after {request.timeout_seconds}s",
                    latency_ms=latency_ms,
                )

            except Exception as exc:
                latency_ms = (time.monotonic() - start_time) * 1000
                trace.append({
                    "venue_id": venue.venue_id,
                    "attempt": attempts,
                    "success": False,
                    "latency_ms": latency_ms,
                    "error": str(exc),
                })
                logger.error("execution exception on venue %s: %s", 
                           venue.venue_id, exc)
                last_result = ExecutionResult(
                    success=False,
                    venue_id=venue.venue_id,
                    error=str(exc),
                    latency_ms=latency_ms,
                )

        # All venues exhausted
        if last_result is None:
            last_result = ExecutionResult(
                success=False,
                venue_id="none",
                error="no venues attempted",
            )

        # Record failed execution trace
        if self._enable_tracing:
            self._execution_log.append({
                "trace_id": trace_id,
                "symbol": request.symbol,
                "side": request.side.value,
                "quantity": request.quantity,
                "result": last_result.to_dict(),
                "trace": trace,
                "timestamp": datetime.now().isoformat(),
            })

        logger.error("all venues exhausted for %s, last error: %s", 
                    request.symbol, last_result.error)
        return last_result

    async def cancel_order(
        self,
        order_id: str,
        venue_id: str | None = None,
    ) -> bool:
        """Cancel an order on a specific venue or try all venues.
        
        Args:
            order_id: The order to cancel
            venue_id: Optional specific venue to try
            
        Returns:
            True if cancellation succeeded
        """
        if venue_id:
            venue = self._registry.get_venue(venue_id)
            if venue:
                return await venue.cancel_order(order_id)
            return False

        # Try all venues
        venues = self._registry.get_all_venues()
        for venue in venues:
            try:
                if await venue.cancel_order(order_id):
                    logger.info("order %s cancelled on venue %s", 
                               order_id, venue.venue_id)
                    return True
            except Exception as exc:
                logger.debug("cancel failed on %s: %s", venue.venue_id, exc)

        return False

    def get_execution_log(
        self,
        *,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get execution history.
        
        Args:
            symbol: Optional filter by symbol
            limit: Maximum results to return
            
        Returns:
            List of execution records
        """
        log = self._execution_log
        if symbol:
            log = [e for e in log if e.get("symbol") == symbol]
        return log[-limit:]

    def get_manifest(self) -> dict[str, Any]:
        """Get driver status manifest.
        
        Returns:
            Dict with driver statistics
        """
        return {
            "max_total_retries": self._max_total_retries,
            "tracing_enabled": self._enable_tracing,
            "execution_log_size": len(self._execution_log),
            "idempotency_cache_size": len(self._idempotency_cache),
            "registry": self._registry.get_manifest(),
        }

    def clear_idempotency_cache(self) -> None:
        """Clear the idempotency cache."""
        self._idempotency_cache.clear()
        logger.info("idempotency cache cleared")


__all__ = ["CrossChainDriver"]
