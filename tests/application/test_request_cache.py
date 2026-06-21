"""RequestCache backed by MemoryCache."""

from __future__ import annotations

from app.application.middleware.request_middleware import RequestCache
from app.infrastructure.memory_cache import clear_cache


def test_request_cache_round_trip():
    clear_cache()
    cache = RequestCache(ttl_seconds=60)
    cache.set("quote:600519", {"price": 10})
    assert cache.get("quote:600519") == {"price": 10}


def test_request_cache_clear():
    clear_cache()
    cache = RequestCache(ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None
