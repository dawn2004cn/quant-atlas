"""Order persistence — file / SQLite / Redis backends for order state and events."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class OrderPersistence:
    """Persist order state and event log across file, SQLite, or Redis backends."""

    def __init__(self, backend: str = "file", path: str = "data/orders", **kwargs: Any) -> None:
        _ = kwargs
        self._backend = backend
        self._path = Path(path)
        self._lock = threading.RLock()

        if backend == "file":
            self._path.mkdir(parents=True, exist_ok=True)
            from .order_persistence_file import FileOrderPersistenceBackend

            state_file = self._path / "order_state.json"
            events_file = self._path / "order_events.jsonl"
            self._file_backend = FileOrderPersistenceBackend(state_file, events_file)
        elif backend == "sqlite":
            from .order_persistence_sqlite import SqliteOrderPersistenceBackend

            self._sqlite_backend = SqliteOrderPersistenceBackend(self._path / "orders.db")
        elif backend == "redis":
            from app.infrastructure.trading.order_persistence_redis import RedisOrderPersistenceBackend

            self._redis_backend = RedisOrderPersistenceBackend()

    def save_state(self, state: dict[str, Any]) -> bool:
        with self._lock:
            try:
                if self._backend == "file":
                    return self._file_backend.save_state(state)
                if self._backend == "sqlite":
                    return self._sqlite_backend.save_state(state)
                if self._backend == "redis":
                    return self._redis_backend.save_state(state)
                logger.error("Unknown backend: %s", self._backend)
                return False
            except Exception as exc:
                logger.error("Failed to save state: %s", exc)
                return False

    def load_state(self) -> dict[str, Any]:
        with self._lock:
            try:
                if self._backend == "file":
                    return self._file_backend.load_state()
                if self._backend == "sqlite":
                    return self._sqlite_backend.load_state()
                if self._backend == "redis":
                    return self._redis_backend.load_state()
                return {}
            except Exception as exc:
                logger.error("Failed to load state: %s", exc)
                return {}

    def save_event(self, event: dict[str, Any]) -> bool:
        with self._lock:
            try:
                if self._backend == "file":
                    return self._file_backend.append_event(event)
                return True
            except Exception as exc:
                logger.error("Failed to save event: %s", exc)
                return False

    def load_events(self, order_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            try:
                if self._backend == "file":
                    return self._file_backend.load_events(order_id)
                return []
            except Exception as exc:
                logger.error("Failed to load events: %s", exc)
                return []


from .global_persistence import GlobalPersistence, get_persistence

__all__ = ["OrderPersistence", "GlobalPersistence", "get_persistence"]
