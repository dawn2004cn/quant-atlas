"""CacheManager L1+L2 facade tests."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.infrastructure.cache.cache_manager import CacheManager


def test_cache_manager_reads_l1_before_l2():
    memory = MagicMock()
    memory.get.return_value = "l1"
    redis = MagicMock()
    mgr = CacheManager(memory=memory, redis_ttl=60, memory_ttl=30)
    mgr._redis = redis

    assert mgr.get("k") == "l1"
    redis.get.assert_not_called()


def test_cache_manager_promotes_l2_hit_to_l1():
    memory = MagicMock()
    memory.get.return_value = None
    redis = MagicMock()
    redis.get.return_value = "l2"
    mgr = CacheManager(memory=memory, redis_ttl=120, memory_ttl=45)
    mgr._redis = redis

    assert mgr.get("k") == "l2"
    memory.set.assert_called_once_with("k", "l2", 45)


def test_cache_manager_writes_both_layers():
    memory = MagicMock()
    redis = MagicMock()
    mgr = CacheManager(memory=memory, redis_ttl=200, memory_ttl=40)
    mgr._redis = redis

    mgr.set("k", {"x": 1}, ttl=100, memory_ttl=20)
    memory.set.assert_called_once_with("k", {"x": 1}, 20)
    redis.set.assert_called_once_with("k", {"x": 1}, 100)
