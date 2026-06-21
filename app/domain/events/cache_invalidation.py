from __future__ import annotations

"""Domain events that drive cache invalidation across modules.

Instead of brittle prefix-based cache clearing, each business operation
publishes a typed CacheInvalidationEvent. An outbox-backed subscriber
consumes these events and selectively purges only the affected cache
namespace — no wildcards needed.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass(frozen=True)
class CacheInvalidationEvent:
    """Domain event signalling that cached data is stale.

    Attributes:
        namespace: Logical cache bucket (e.g. "market:panorama", "quote:600519").
        aggregate_type: Business entity that changed (e.g. "stock", "strategy").
        aggregate_id: Entity identifier (e.g. "600519.SH", "ma_cross").
        reason: Human-readable explanation for audit trails.
        invalidated_keys: Optional explicit key patterns to purge.
        occurred_at: Event timestamp (UTC).
    """

    namespace: str
    aggregate_type: str
    aggregate_id: str
    reason: str = ""
    invalidated_keys: list[str] = field(default_factory=list)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        """Return a stable event type for the bus."""
        return "CacheInvalidationEvent"

    def to_payload(self) -> dict:
        """Serialize for outbox storage."""
        return {
            "namespace": self.namespace,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "reason": self.reason,
            "invalidated_keys": self.invalidated_keys,
            "occurred_at": self.occurred_at.isoformat(),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> CacheInvalidationEvent:
        """Deserialize from outbox payload."""
        return cls(
            namespace=payload["namespace"],
            aggregate_type=payload["aggregate_type"],
            aggregate_id=payload["aggregate_id"],
            reason=payload.get("reason", ""),
            invalidated_keys=payload.get("invalidated_keys", []),
            occurred_at=datetime.fromisoformat(payload["occurred_at"]),
        )


# ── Convenience constructors ──────────────────────────────────────────


def invalidate_market_panorama(market: str) -> CacheInvalidationEvent:
    """Emit when market data changes significantly."""
    return CacheInvalidationEvent(
        namespace=f"market:panorama:{market}",
        aggregate_type="market",
        aggregate_id=market,
        reason="Market data refreshed",
        invalidated_keys=[f"market:panorama:{market}"],
    )


def invalidate_quote(symbol: str, market: str) -> CacheInvalidationEvent:
    """Emit when a quote or k-line is updated."""
    return CacheInvalidationEvent(
        namespace=f"quote:{symbol}",
        aggregate_type="quote",
        aggregate_id=symbol,
        reason=f"Quote updated for {symbol}",
        invalidated_keys=[f"quote:{symbol}"],
    )


def invalidate_strategy_cache(strategy_id: str) -> CacheInvalidationEvent:
    """Emit when a strategy's parameters or results change."""
    return CacheInvalidationEvent(
        namespace=f"strategy:{strategy_id}",
        aggregate_type="strategy",
        aggregate_id=strategy_id,
        reason="Strategy cache invalidated",
        invalidated_keys=[f"strategy:{strategy_id}*"],
    )
