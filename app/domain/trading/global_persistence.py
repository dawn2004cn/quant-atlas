"""Singleton wrapper for OrderPersistence (R17 slice)."""

from __future__ import annotations

import threading

from .order_persistence import OrderPersistence


class GlobalPersistence:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._persistence = OrderPersistence(**kwargs)
        return cls._instance

    def __getattr__(self, name: str):
        return getattr(self._persistence, name)


def get_persistence(**kwargs) -> OrderPersistence:
    """Create global persistence."""
    return GlobalPersistence(**kwargs)


__all__ = ["GlobalPersistence", "get_persistence"]
