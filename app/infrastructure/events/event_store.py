from __future__ import annotations

"""Event Store - Infrastructure for persisting domain events.

Provides event store with persistence and replay capability.
"""


import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.events.handlers import DomainEvent, EventBus

logger = get_logger(__name__)


class EventStoreError(Exception):
    """Event store error."""
    pass


class EventNotFoundError(EventStoreError):
    """Event not found."""
    pass


class EventStore:
    """Event store with persistence."""

    def __init__(self, storage_path: Path | None = None):
        self._storage_path = storage_path
        self._events: list[dict] = []
        self._subscribers: dict[str, list[Callable]] = {}
        self._event_bus = EventBus()

        if storage_path and storage_path.exists():
            self._load()

    def _load(self) -> None:
        """Load events from storage."""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, encoding="utf-8") as f:
                data = json.load(f)
                self._events = data.get("events", [])
                logger.info(f"Loaded {len(self._events)} events from {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to load events: {e}")

    def _save(self) -> None:
        """Save events to storage."""
        if not self._storage_path:
            return

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"events": self._events, "saved_at": datetime.now().isoformat()},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save events: {e}")

    def append(self, event: DomainEvent, aggregate_id: str | None = None) -> None:
        """Append an event."""
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "aggregate_id": aggregate_id or "",
            "occurred_at": event.occurred_at.isoformat(),
            "metadata": event.metadata,
        }

        self._events.append(event_data)

        self._event_bus.publish(event)

        self._notify_subscribers(event)

        if self._storage_path:
            self._save()

        logger.debug(f"Appended: {event.event_type}")

    def _notify_subscribers(self, event: DomainEvent) -> None:
        """Notify subscribers."""
        event_type = event.event_type
        subscribers = self._subscribers.get(event_type, [])

        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

    def subscribe(self, event_type: str, callback: Callable) -> EventStore:
        """Subscribe to event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        return self

    def get_events(
        self,
        aggregate_id: str | None = None,
        event_type: str | None = None,
        since: datetime | None = None
    ) -> list[dict]:
        """Get events with filters."""
        result = self._events

        if aggregate_id:
            result = [e for e in result if e.get("aggregate_id") == aggregate_id]

        if event_type:
            result = [e for e in result if e.get("event_type") == event_type]

        if since:
            result = [
                e for e in result
                if datetime.fromisoformat(e.get("occurred_at", "")) >= since
            ]

        return result

    def replay(
        self,
        aggregate_id: str,
        rebuild_fn: Callable[[list[dict]], Any]
    ) -> Any:
        """Replay events to rebuild aggregate."""
        events = self.get_events(aggregate_id=aggregate_id)

        if not events:
            raise EventNotFoundError(f"No events for aggregate: {aggregate_id}")

        return rebuild_fn(events)

    def get_event_count(self, aggregate_id: str | None = None) -> int:
        """Get event count."""
        if aggregate_id:
            return len(self.get_events(aggregate_id=aggregate_id))
        return len(self._events)

    def clear(self) -> None:
        """Clear all events."""
        self._events.clear()

        if self._storage_path:
            self._save()

        logger.info("Event store cleared")

    def export(self) -> list[dict]:
        """Export all events."""
        return self._events.copy()

    def import_events(self, events: list[dict]) -> None:
        """Import events."""
        self._events.extend(events)

        if self._storage_path:
            self._save()

        logger.info(f"Imported {len(events)} events")


class InMemoryEventStore(EventStore):
    """In-memory event store (no persistence)."""

    def __init__(self):
        super().__init__(storage_path=None)


class FileEventStore(EventStore):
    """File-based event store."""

    def __init__(self, storage_path: Path):
        super().__init__(storage_path=storage_path)


def create_event_store(store_type: str = "memory", **kwargs) -> EventStore:
    """Factory for creating event store."""
    if store_type == "memory":
        return InMemoryEventStore()
    elif store_type == "file":
        return FileEventStore(storage_path=kwargs.get("path", Path("instance/events.json")))
    else:
        raise ValueError(f"Unknown store type: {store_type}")


_global_event_store: EventStore | None = None


def get_event_store() -> EventStore:
    """Get global event store."""
    global _global_event_store
    if _global_event_store is None:
        _global_event_store = InMemoryEventStore()
    return _global_event_store


__all__ = [
    "EventStore",
    "EventStoreError",
    "EventNotFoundError",
    "InMemoryEventStore",
    "FileEventStore",
    "create_event_store",
    "get_event_store",
]
