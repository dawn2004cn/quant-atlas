from __future__ import annotations

"""Event middleware for cross-cutting concerns."""


import time
from datetime import datetime

from app.application.events.event_bus import Event
from app.core.logger import get_logger

logger = get_logger(__name__)


def event_logging_middleware(event: Event) -> Event | None:
    """Log all events with timing information."""
    time.perf_counter()

    # Add timing metadata
    event.payload['_timing'] = {
        'received_at': datetime.now().isoformat(),
    }

    logger.debug(
        "Event received: type=%s source=%s payload_keys=%s",
        event.type.value,
        event.source,
        list(event.payload.keys())
    )

    return event


def event_metrics_middleware(event: Event) -> Event | None:
    """Track event metrics (could be sent to Prometheus, etc.)."""
    # In production, this would send to metrics system
    # For now, just log slow events
    try:
        payload = event.payload
        # Add metrics data
        payload['_metrics'] = {
            'event_type': event.type.value,
            'source': event.source,
            'size_bytes': len(str(payload)),
        }
    except Exception as e:
        logger.warning("middleware.py.event_metrics_middleware: %s", e)

    return event


def event_validation_middleware(event: Event) -> Event | None:
    """Validate event structure."""
    if not event.type:
        logger.warning("Event missing type, filtering out")
        return None

    if not event.payload:
        logger.warning("Event %s has no payload", event.type.value)
        return None

    return event


def event_filter_middleware(event: Event) -> Event | None:
    """Filter out test events in production."""
    # Filter test events in production
    if event.source == 'test' and not __debug__:
        return None

    return event


def setup_event_middleware(bus) -> None:
    """Setup all middleware for the event bus."""
    # Order matters - validation first, then logging, then metrics
    bus.add_middleware(event_validation_middleware)
    bus.add_middleware(event_filter_middleware)
    bus.add_middleware(event_logging_middleware)
    bus.add_middleware(event_metrics_middleware)
