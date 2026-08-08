from __future__ import annotations

"""Short-TTL coalesced fetch for OHLCV history (thundering-herd guard)."""

import threading
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_registry_lock = threading.Lock()
_key_locks: dict[str, threading.Lock] = {}
_mem: dict[str, tuple[float, T]] = {}
_DEFAULT_TTL = 45.0


def get_history_coalesced(
    key: str,
    factory: Callable[[], T],
    *,
    ttl: float = _DEFAULT_TTL,
) -> T:
    """Return cached history or compute once per key under concurrent load."""
    now = time.time()
    with _registry_lock:
        hit = _mem.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]

    with _registry_lock:
        lock = _key_locks.setdefault(key, threading.Lock())

    with lock:
        now = time.time()
        hit = _mem.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
        value = factory()
        _mem[key] = (time.time(), value)
        return value
