"""Cache coalescing (thundering herd) tests."""
from __future__ import annotations

import threading
from unittest.mock import MagicMock

from app.infrastructure.cache.cache_manager import CacheManager
from app.infrastructure.cache.coalesce import get_or_set_coalesced


def test_get_or_set_coalesced_runs_factory_once():
    calls = {"n": 0}
    store: dict[str, int] = {}

    def factory() -> int:
        calls["n"] += 1
        return 42

    def worker() -> None:
        get_or_set_coalesced(
            "k",
            get_value=lambda: store.get("k"),
            set_value=lambda v: store.__setitem__("k", v),
            factory=factory,
        )

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert calls["n"] == 1
    assert store["k"] == 42


def test_cache_manager_get_or_set_coalesced():
    memory = MagicMock()
    memory.get.return_value = None
    redis = MagicMock()
    redis.get.return_value = None
    factory_calls = {"n": 0}

    def factory() -> dict[str, int]:
        factory_calls["n"] += 1
        return {"v": 1}

    mgr = CacheManager(memory=memory, redis_ttl=60, memory_ttl=30)
    mgr._redis = redis

    result = mgr.get_or_set("key", factory, ttl=90)
    assert result == {"v": 1}
    assert factory_calls["n"] == 1
