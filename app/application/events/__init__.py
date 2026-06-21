"""Events module - Event-driven architecture components.

Usage:
    from app.application.events import EventBus, EventType, publish_event

    # Subscribe to events
    @EventBus().subscribe(EventType.DATA_SYNCED)
    def handle_sync(event):
        logger.debug("Data synced! %s", event.payload)

    # Publish events
    publish_event(EventType.QUOTE_UPDATED, {"code": "600519", "price": 1800}, source="MyService")
"""

from .event_bus import (
    EventBus,
    Event,
    EventType,
    get_event_bus,
    publish_event,
    on_event,
)

from .handlers import EventHandlerRegistry, get_event_handlers

from .workflows import get_workflows

__all__ = [
    'EventBus',
    'Event',
    'EventType',
    'get_event_bus',
    'publish_event',
    'on_event',
    'EventHandlerRegistry',
    'get_event_handlers',
    'get_workflows',
]