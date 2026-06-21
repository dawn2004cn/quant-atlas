from __future__ import annotations
"""Event Bus for decoupled service communication."""


import logging
from typing import Any, Callable, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

from app.core.logger import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """System event types."""
    # Data events
    DATA_SYNCED = "data_synced"
    DATA_SYNC_FAILED = "data_sync_failed"
    QUOTE_UPDATED = "quote_updated"
    HISTORY_UPDATED = "history_updated"

    # Market events
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    MARKET_REGIME_CHANGED = "market_regime_changed"
    MARKET_SENTIMENT_UPDATED = "market_sentiment_updated"

    # Trading events
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_EXPIRED = "signal_expired"
    SIGNALS_BATCH_PROCESSED = "signals_batch_processed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_UPDATED = "position_updated"

    # Risk events
    RISK_ALERT = "risk_alert"
    RISK_THRESHOLD_BREACHED = "risk_threshold_breached"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"

    # Analysis events
    ANALYSIS_COMPLETED = "analysis_completed"
    SCAN_COMPLETED = "scan_completed"
    REPORT_GENERATED = "report_generated"

    # Task events
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_SCHEDULED = "task_scheduled"

    # User events
    WATCHLIST_UPDATED = "watchlist_updated"
    ALERT_TRIGGERED = "alert_triggered"
    NOTIFICATION_SENT = "notification_sent"


@dataclass
class Event:
    """Base event class."""
    type: EventType
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    correlation_id: str | None = None


class EventBus:
    """Simple in-memory event bus for service decoupling.
    
    Usage:
        # In service that publishes events
        event_bus = get_event_bus()
        event_bus.publish(Event(
            type=EventType.DATA_SYNCED,
            payload={"market": "CN", "records": 100},
            source="TdxSyncService"
        ))
        
        # In service that subscribes to events
        @event_bus.subscribe(EventType.DATA_SYNCED)
        def handle_data_sync(event: Event):
            # Do something when data is synced
            pass
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers: Dict[EventType, List[Callable]] = defaultdict(list)
            cls._instance._middleware: List[Callable] = []
            cls._instance._history: List[Event] = []
            cls._instance._max_history = 100
        return cls._instance

    def subscribe(self, event_type: EventType) -> Callable:
        """Decorator to subscribe to an event type."""
        def decorator(func: Callable):
            self._handlers[event_type].append(func)
            logger.debug("Subscribed %s to %s", func.__name__, event_type.value)
            return func
        return decorator

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        logger.debug("Publishing event: %s from %s", event.type.value, event.source)

        # Run middleware
        for middleware in self._middleware:
            try:
                event = middleware(event)
                if event is None:
                    logger.debug("Event filtered by middleware")
                    return
            except Exception as e:
                logger.warning("Middleware error: %s", e)

        # Store in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Notify handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(handler):
                    try:
                        asyncio.get_running_loop()
                        asyncio.create_task(handler(event))
                    except RuntimeError:
                        from app.application.request_executor import run_async

                        run_async(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error("Event handler error: %s in %s", e, handler.__name__)

    def add_middleware(self, middleware: Callable[[Event], Event | None]) -> None:
        """Add middleware to process events before handlers."""
        self._middleware.append(middleware)

    def get_history(self, event_type: EventType | None = None, limit: int = 20) -> List[Event]:
        """Get event history."""
        if event_type:
            return [e for e in self._history if e.type == event_type][-limit:]
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()

    def list_handler_keys(self) -> list[str]:
        """Return all registered event-type keys (value strings)."""
        return sorted(set(e.value for e in self._handlers))


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return EventBus()


# Convenience decorators
def on_event(event_type: EventType) -> Callable:
    """Short-hand decorator for subscribing to events."""
    return get_event_bus().subscribe(event_type)


def publish_event(event_type: EventType, payload: dict, source: str, correlation_id: str | None = None) -> None:
    """Publish an event using the global event bus."""
    event = Event(
        type=event_type,
        payload=payload,
        source=source,
        correlation_id=correlation_id
    )
    get_event_bus().publish(event)