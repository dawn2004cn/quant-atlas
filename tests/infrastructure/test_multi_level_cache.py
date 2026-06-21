"""MultiLevelCache L1 delegation tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.infrastructure.cache.multi_level_cache import CacheConfig, MultiLevelCache


def test_multi_level_cache_l1_hit_skips_redis():
    cache = MultiLevelCache(config=CacheConfig(enable_redis=False))
    cache.set("ns", "k", {"v": 1}, ttl=120)
    assert cache.get("ns", "k") == {"v": 1}


def test_multi_level_cache_promotes_redis_to_l1():
    cache = MultiLevelCache(config=CacheConfig(enable_memory=True, enable_redis=True))
    redis = MagicMock()
    redis.get.return_value = '{"v": 2}'
    cache._redis_client = redis

    assert cache.get("ns", "k2") == {"v": 2}
    assert cache._l1.get("cache:ns:k2") == {"v": 2}
    redis.get.assert_called_once()


def test_multi_level_cache_invalidate_namespace_clears_l1():
    cache = MultiLevelCache(config=CacheConfig(enable_redis=False))
    cache.set("alpha", "one", 1)
    cache.set("alpha", "two", 2)
    cache.set("beta", "x", 3)

    cache.invalidate_namespace("alpha")

    assert cache.get("alpha", "one") is None
    assert cache.get("beta", "x") == 3
