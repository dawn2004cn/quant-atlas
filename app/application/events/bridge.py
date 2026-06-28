"""Bridge between application event bus and core event bus.

Translates application events to core events and forwards to WebSocket.
Preserves semantic type + payload via ApplicationEventForwardedEvent.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.events.event_bus import Event, EventType
from app.application.events.event_bus import get_event_bus as get_app_event_bus
from app.core.event_bus import (
    ApplicationEventForwardedEvent,
    MarketDataUpdatedEvent,
    MarketRegimeChangedEvent,
)
from app.core.event_bus import (
    get_event_bus as get_core_event_bus,
)
from app.core.logger import get_logger

logger = get_logger(__name__)

CoreEventFactory = Callable[[Event], Any]


def _market_data_from_payload(event: Event, *, source: str) -> MarketDataUpdatedEvent:
    payload = event.payload or {}
    core = MarketDataUpdatedEvent(
        source=source,
        symbol=str(payload.get("symbol") or ""),
        market=str(payload.get("market") or "CN"),
    )
    core.source = event.source or source
    core.timestamp = event.timestamp
    return core


def _regime_from_payload(event: Event) -> MarketRegimeChangedEvent:
    payload = event.payload or {}
    core = MarketRegimeChangedEvent(
        previous_regime=str(payload.get("previous_regime") or payload.get("old_regime") or ""),
        new_regime=str(payload.get("new_regime") or payload.get("regime") or ""),
        market=str(payload.get("market") or "CN"),
        confidence=float(payload.get("confidence") or 0.0),
        trigger_reason=str(payload.get("trigger_reason") or payload.get("reason") or ""),
    )
    core.source = event.source
    core.timestamp = event.timestamp
    return core


def _forward_preserved(event: Event) -> ApplicationEventForwardedEvent:
    core = ApplicationEventForwardedEvent(
        app_event_type=event.type.value,
        payload=dict(event.payload or {}),
    )
    core.source = event.source
    core.timestamp = event.timestamp
    return core


# Specialized mappers keep rich semantics; default preserves full payload.
EVENT_TYPE_MAPPING: dict[EventType, CoreEventFactory] = {
    EventType.DATA_SYNCED: lambda e: _market_data_from_payload(e, source="scanner"),
    EventType.QUOTE_UPDATED: lambda e: _market_data_from_payload(e, source="quote_broadcast"),
    EventType.MARKET_SENTIMENT_UPDATED: lambda e: _market_data_from_payload(e, source="sentiment"),
    EventType.SCAN_COMPLETED: lambda e: _forward_preserved(e),
    EventType.SIGNALS_BATCH_PROCESSED: lambda e: _forward_preserved(e),
    EventType.MARKET_REGIME_CHANGED: _regime_from_payload,
    EventType.SIGNAL_GENERATED: lambda e: _forward_preserved(e),
    EventType.RISK_ALERT: lambda e: _forward_preserved(e),
    EventType.ANALYSIS_COMPLETED: lambda e: _forward_preserved(e),
    EventType.WATCHLIST_UPDATED: lambda e: _forward_preserved(e),
}

_app_bus = None
_core_bus = None


def _get_app_bus():
    global _app_bus
    if _app_bus is None:
        _app_bus = get_app_event_bus()
    return _app_bus


def _get_core_bus():
    global _core_bus
    if _core_bus is None:
        _core_bus = get_core_event_bus()
    return _core_bus


def forward_event(event: Event) -> None:
    """Forward an application event to core event bus for WebSocket broadcast."""
    mapper = EVENT_TYPE_MAPPING.get(event.type)
    if not mapper:
        return
    try:
        core_event = mapper(event)
        _get_core_bus().publish(core_event)
    except Exception as exc:
        logger.exception("Event bridge forward failed for %s: %s", event.type.value, exc)


def setup_event_bridge() -> None:
    """Setup the bridge - call once during app startup."""
    app_bus = _get_app_bus()

    for event_type in EVENT_TYPE_MAPPING:
        app_bus.subscribe(event_type)(forward_event)

    logger.info(
        "Application -> Core event bus bridge established (%d mapped types)",
        len(EVENT_TYPE_MAPPING),
    )


def get_event_bridge_status() -> dict[str, Any]:
    """Get bridge status for monitoring."""
    return {
        "mapped_types": [e.value for e in EVENT_TYPE_MAPPING],
        "app_bus_handlers": len(_get_app_bus()._handlers),
    }
