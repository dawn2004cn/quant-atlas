from __future__ import annotations
"""Single-flight (thundering-herd) guard for cache get-or-set paths."""

import threading
from typing import Callable, TypeVar

T = TypeVar("T")

_registry_lock = threading.Lock()
_key_locks: dict[str, threading.Lock] = {}


def get_or_set_coalesced(
    key: str,
    *,
    get_value: Callable[[], T | None],
    set_value: Callable[[T], None],
    factory: Callable[[], T],
) -> T:
    """Return cached value or compute once per key under concurrent load."""
    hit = get_value()
    if hit is not None:
        return hit

    with _registry_lock:
        lock = _key_locks.setdefault(key, threading.Lock())

    with lock:
        hit = get_value()
        if hit is not None:
            return hit
        value = factory()
        set_value(value)
        return value
