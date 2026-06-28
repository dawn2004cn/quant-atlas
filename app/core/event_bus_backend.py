"""EventBus backend abstraction.

The current ``EventBus`` in ``app/core/event_bus.py`` is an in-memory
singleton — all subscriptions and recent-event history are lost on process
restart. This module introduces a backend protocol so the bus can be backed
by a persistent store (Redis Streams, Kafka, etc.) in the future without
changing the public ``EventBus`` API.

Phase 2.2 only ships the interface and an in-memory implementation that
mirrors the current behavior. The Redis Streams backend is a skeleton that
logs a warning when instantiated; full implementation is deferred to a
later phase.
"""

from __future__ import annotations

import json
import threading
from collections import deque
from typing import Any, Protocol, runtime_checkable
from collections.abc import Callable

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime

logger = get_logger(__name__)


@runtime_checkable
class EventBusBackend(Protocol):
    """Storage backend contract for EventBus subscriptions and history."""

    def add_subscription(
        self,
        event_name: str,
        handler: Callable[[Any], None],
        *,
        priority: int = 0,
    ) -> None: ...

    def remove_subscription(
        self, event_name: str, handler: Callable[[Any], None]
    ) -> None: ...

    def get_subscriptions(self, event_name: str) -> list[tuple[int, Callable[[Any], None]]]: ...

    def record_event(self, event_dict: dict[str, Any]) -> None: ...

    def record_handler_failure(self, failure: dict[str, Any]) -> None: ...

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]: ...

    def handler_failures(self, limit: int = 50) -> list[dict[str, Any]]: ...

    def subscriber_counts(self) -> dict[str, int]: ...

    def clear(self) -> None: ...


class InMemoryBackend:
    """Process-local backend mirroring the historical EventBus behavior.

    Subscriptions, recent events, and handler failures live in memory and are
    lost when the process exits. This is the default backend.
    """

    def __init__(self):
        self._subscribers: dict[str, list[tuple[int, Callable[[Any], None]]]] = {}
        self._recent_events: deque = deque(maxlen=200)
        self._handler_failures: deque = deque(maxlen=100)
        self._lock = threading.Lock()

    def add_subscription(
        self,
        event_name: str,
        handler: Callable[[Any], None],
        *,
        priority: int = 0,
    ) -> None:
        with self._lock:
            existing = [h for _, h in self._subscribers.get(event_name, [])]
            if handler in existing:
                return
            self._subscribers.setdefault(event_name, []).append((priority, handler))
            self._subscribers[event_name].sort(key=lambda pair: pair[0], reverse=True)

    def remove_subscription(self, event_name: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            if event_name not in self._subscribers:
                return
            self._subscribers[event_name] = [
                (p, h) for p, h in self._subscribers[event_name] if h is not handler
            ]

    def get_subscriptions(
        self, event_name: str
    ) -> list[tuple[int, Callable[[Any], None]]]:
        with self._lock:
            return list(self._subscribers.get(event_name, []))

    def record_event(self, event_dict: dict[str, Any]) -> None:
        with self._lock:
            self._recent_events.appendleft(event_dict)

    def record_handler_failure(self, failure: dict[str, Any]) -> None:
        with self._lock:
            self._handler_failures.appendleft(failure)

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        lim = min(max(1, limit), 200)
        with self._lock:
            return list(self._recent_events)[:lim]

    def handler_failures(self, limit: int = 50) -> list[dict[str, Any]]:
        lim = min(max(1, limit), 100)
        with self._lock:
            return list(self._handler_failures)[:lim]

    def subscriber_counts(self) -> dict[str, int]:
        with self._lock:
            return {name: len(handlers) for name, handlers in self._subscribers.items()}

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()
            self._recent_events.clear()
            self._handler_failures.clear()


class RedisStreamBackend:
    """Persistent backend backed by Redis Streams.

    Phase 2.2 ships only the skeleton. Instantiating this backend logs a
    warning and falls back to ``InMemoryBackend`` behavior until the full
    implementation (stream XADD / XREADGROUP consumer groups, subscription
    replay on restart) lands in a later phase.
    """

    def __init__(self, redis_url: str | None = None):
        logger.warning(
            "RedisStreamBackend is a skeleton in Phase 2.2; "
            "falling back to in-memory behavior. Set EVENT_BUS_BACKEND=memory "
            "to silence this warning."
        )
        self._fallback = InMemoryBackend()
        self._redis_url = redis_url or get_runtime("REDIS_URL", "")
        self._stream_key = "event_bus:events"
        self._client = None
        if self._redis_url:
            try:
                from app.infrastructure.redis_client import RedisClientPool

                self._client = RedisClientPool.get(self._redis_url).client
            except Exception:
                logger.warning(
                    "RedisStreamBackend could not connect to Redis; using in-memory fallback",
                    exc_info=True,
                )
                self._client = None

    def add_subscription(self, event_name, handler, *, priority=0):
        self._fallback.add_subscription(event_name, handler, priority=priority)

    def remove_subscription(self, event_name, handler):
        self._fallback.remove_subscription(event_name, handler)

    def get_subscriptions(self, event_name):
        return self._fallback.get_subscriptions(event_name)

    def record_event(self, event_dict):
        self._fallback.record_event(event_dict)
        if self._client is not None:
            try:
                self._client.xadd(self._stream_key, {"payload": json.dumps(event_dict)})
            except Exception:
                logger.debug("RedisStreamBackend XADD failed", exc_info=True)

    def record_handler_failure(self, failure):
        self._fallback.record_handler_failure(failure)

    def recent_events(self, limit=50):
        return self._fallback.recent_events(limit)

    def handler_failures(self, limit=50):
        return self._fallback.handler_failures(limit)

    def subscriber_counts(self):
        return self._fallback.subscriber_counts()

    def clear(self):
        self._fallback.clear()


_backend: EventBusBackend | None = None


def get_event_bus_backend() -> EventBusBackend:
    """Return the configured EventBus backend.

    Backend selection (env var ``EVENT_BUS_BACKEND``):
    - ``memory`` (default): process-local in-memory store.
    - ``redis``: Redis Streams backed store (skeleton in Phase 2.2).
    """
    global _backend
    if _backend is not None:
        return _backend

    choice = (get_runtime("EVENT_BUS_BACKEND", "memory") or "memory").strip().lower()
    if choice == "redis":
        _backend = RedisStreamBackend()
    else:
        _backend = InMemoryBackend()
    logger.debug("EventBus backend selected: %s", type(_backend).__name__)
    return _backend


def reset_event_bus_backend() -> None:
    """Clear the cached backend (tests only)."""
    global _backend
    _backend = None
