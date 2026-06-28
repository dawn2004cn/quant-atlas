from __future__ import annotations
"""Domain Event Handlers.

In-memory event bus for domain events.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections.abc import Callable


from app.core.logger import get_logger

logger = get_logger(__name__)


class EventPriority(str, Enum):
    """Event priority."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class DomainEvent:
    """Base domain event."""
    event_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S%f"))
    occurred_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__


@dataclass
class StockCreatedEvent(DomainEvent):
    """Stock created event."""
    stock_code: str = ""
    name: str = ""
    market: str = ""


@dataclass
class SignalGeneratedEvent(DomainEvent):
    """Signal generated event."""
    stock_code: str = ""
    signal_type: str = ""
    confidence: float = 0.0
    source: str = ""


@dataclass
class PositionOpenedEvent(DomainEvent):
    """Position opened event."""
    stock_code: str = ""
    quantity: float = 0.0
    price: float = 0.0


@dataclass
class PositionClosedEvent(DomainEvent):
    """Position closed event."""
    stock_code: str = ""
    quantity: float = 0.0
    pnl: float = 0.0


@dataclass
class OrderSubmittedEvent(DomainEvent):
    """Order submitted event."""
    order_id: str = ""
    stock_code: str = ""
    side: str = ""
    quantity: float = 0.0


@dataclass
class OrderFilledEvent(DomainEvent):
    """Order filled event."""
    order_id: str = ""
    stock_code: str = ""
    quantity: float = 0.0
    price: float = 0.0


class EventHandler(ABC):
    """Event handler interface."""

    @abstractmethod
    def handle(self, event: DomainEvent) -> None:
        """Handle an event."""
        pass

    @property
    @abstractmethod
    def priority(self) -> EventPriority:
        """Handler priority."""
        pass


class LoggingEventHandler(EventHandler):
    """Log all events."""

    @property
    def priority(self) -> EventPriority:
        return EventPriority.LOW

    def handle(self, event: DomainEvent) -> None:
        logger.info(f"Event: {event.event_type} - {event.metadata}")


class EventBus:
    """In-memory event bus."""

    def __init__(self):
        self._handlers: list[EventHandler] = []
        self._listeners: dict[str, list[Callable]] = {}
        self._event_history: list[DomainEvent] = []
        self._max_history: int = 1000

    def subscribe(self, handler: EventHandler) -> EventBus:
        """Subscribe a handler."""
        self._handlers.append(handler)
        self._handlers.sort(key=lambda h: h.priority.value)
        return self

    def listen(self, event_type: str, callback: Callable) -> EventBus:
        """Listen for specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        return self

    def publish(self, event: DomainEvent) -> None:
        """Publish an event."""
        self._event_history.append(event)

        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        for handler in self._handlers:
            try:
                handler.handle(event)
            except Exception as e:
                logger.error(f"Handler error: {e}")

        listeners = self._listeners.get(event.event_type, [])
        for callback in listeners:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Listener error: {e}")

        logger.debug(f"Published: {event.event_type}")

    def get_history(
        self,
        event_type: str | None = None,
        limit: int = 100
    ) -> list[DomainEvent]:
        """Get event history."""
        result = self._event_history

        if event_type:
            result = [e for e in result if e.event_type == event_type]

        return result[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()

    @property
    def event_count(self) -> int:
        return len(self._event_history)


_global_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get global event bus."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
        _global_event_bus.subscribe(LoggingEventHandler())
    return _global_event_bus


def publish_event(event: DomainEvent) -> None:
    """Publish event to global bus."""
    get_event_bus().publish(event)


__all__ = [
    "DomainEvent",
    "StockCreatedEvent",
    "SignalGeneratedEvent",
    "PositionOpenedEvent",
    "PositionClosedEvent",
    "OrderSubmittedEvent",
    "OrderFilledEvent",
    "EventHandler",
    "LoggingEventHandler",
    "EventBus",
    "EventPriority",
    "get_event_bus",
    "publish_event",
]
