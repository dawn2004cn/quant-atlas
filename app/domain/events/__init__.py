"""Domain events — re-exports for backward compatibility.

Primary event bus: ``app.core.event_bus`` (dataclass events with priority/TTL/JSON).
Legacy ``EventType`` enum and ``emit``/``on`` helpers live here for
transitional consumption; new code should use ``app.core.event_bus`` directly.
"""

from app.core.logger import get_logger

from .handlers import (
    EventBus,
    DomainEvent,
    EventHandler,
    EventPriority,
    SignalGeneratedEvent,
    PositionOpenedEvent,
    PositionClosedEvent,
    get_event_bus,
    publish_event,
)
from app.core.event_bus import (
    ArbiterConsensusEvent,
    PositionChangedEvent,
    TradeExecutedEvent,
    TruthDeviationEvent,
)

logger = get_logger(__name__)

# ── Legacy EventType compatibility shim ────────────────────────────────────
# Maps the old application-domain EventType values to core event classes.
# Consumers that still use ``EventType.X`` will get these; they are NOT
# wired into the core EventBus (which uses dataclass types instead).

from enum import Enum


class _LegacyEventType(Enum):
    """Compatibility EventType for legacy consumers.

    These values mirror the old ``application.events.EventType`` so that
    code still referencing ``EventType.SIGNAL_GENERATED`` etc. won't crash
    at import time.  They carry no runtime subscription behaviour —
    the bridge (``application.events.bridge``) handles forwarding.
    """

    DATA_SYNCED = "data_synced"
    QUOTE_UPDATED = "quote_updated"
    HISTORY_UPDATED = "history_updated"
    MARKET_REGIME_CHANGED = "market_regime_changed"
    SIGNAL_GENERATED = "signal_generated"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    RISK_ALERT = "risk_alert"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    ALERT_TRIGGERED = "alert_triggered"
    WATCHLIST_UPDATED = "watchlist_updated"


# Re-export as ``EventType`` for backward-compatible ``from app.domain.events import EventType``
EventType = _LegacyEventType


def _emit_legacy(event_name: str, **data: object) -> None:
    """Compat shim for the old ``emit()`` — forwards via the bridge."""
    from app.application.events.bridge import forward_event
    from app.application.events.event_bus import Event, EventType as _AppEventType

    try:
        app_type = _AppEventType(event_name)
        forward_event(Event(type=app_type, payload=dict(data), source="legacy_emit"))
    except ValueError:
        logger.debug("Event name not in app EventType: %s", event_name)  # silently ignore unknown event type


def _on_legacy(event_name: str):
    """Compat shim for the old ``on()`` decorator — no-op (legacy bus not wired)."""
    def decorator(func):
        return func
    return decorator


__all__ = [
    "EventBus",
    "DomainEvent",
    "EventHandler",
    "EventPriority",
    "SignalGeneratedEvent",
    "PositionOpenedEvent",
    "PositionClosedEvent",
    "ArbiterConsensusEvent",
    "PositionChangedEvent",
    "TradeExecutedEvent",
    "TruthDeviationEvent",
    "get_event_bus",
    "publish_event",
    "EventType",
    "emit",
    "on",
    # Cache invalidation
    "CacheInvalidationEvent",
    "invalidate_market_panorama",
    "invalidate_quote",
    "invalidate_strategy_cache",
    "CacheInvalidationEmitter",
    "CacheInvalidationTransaction",
    "CacheInvalidationSubscriber",
    "CacheInvalidationPublisher",
]


# Aliases for legacy consumers that do ``from app.domain.events import emit, on``
emit = _emit_legacy
on = _on_legacy

# ── Cache invalidation re-exports ────────────────────────────────────
from .cache_invalidation import (  # noqa: E402
    CacheInvalidationEvent,
    invalidate_market_panorama,
    invalidate_quote,
    invalidate_strategy_cache,
)
from .cache_invalidation_emitter import (  # noqa: E402
    CacheInvalidationEmitter,
    CacheInvalidationTransaction,
)
from .cache_invalidation_subscriber import (  # noqa: E402
    CacheInvalidationSubscriber,
)
from .cache_invalidation_publisher import (  # noqa: E402
    CacheInvalidationPublisher,
)