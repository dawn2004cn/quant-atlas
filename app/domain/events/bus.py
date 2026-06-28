from __future__ import annotations

"""Domain Events and Event Bus."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class DomainEvent:
    """Base class for all domain events."""
    pass

class EventBus:
    """Lightweight in-memory event bus."""

    def __init__(self):
        self._subscribers: dict[type[DomainEvent], list[Callable]] = {}

    def subscribe(self, event_type: type[DomainEvent], callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event: DomainEvent):
        event_type = type(event)
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                callback(event)

# Global event bus
bus = EventBus()
