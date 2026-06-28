from __future__ import annotations

"""Multi-level cache abstraction with Redis backend and Pydantic model serialization."""


import hashlib
import json
from typing import Any, Generic, TypeVar

import redis

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.infrastructure.cache.coalesce import get_or_set_coalesced
from app.infrastructure.memory_cache import get_cache
from app.infrastructure.redis_client import RedisClientPool, delete_keys_by_pattern

logger = get_logger(__name__)

T = TypeVar("T")


class CacheLevel:
    """Cache level constants."""
    MEMORY = "memory"
    REDIS = "redis"


class CacheConfig:
    """Configuration for multi-level cache."""

    def __init__(
        self,
        redis_url: str | None = None,
        enable_redis: bool = True,
        enable_memory: bool = True,
        default_ttl: int = 300,
        memory_max_size: int = 1000,
    ):
        self.redis_url = redis_url or get_runtime("REDIS_URL", "")
        self.enable_redis = enable_redis
        self.enable_memory = enable_memory
        self.default_ttl = default_ttl
        self.memory_max_size = memory_max_size


class MultiLevelCache(Generic[T]):
    """Multi-level cache: L1 memory (LRU) + L2 Redis.

    Uses Pydantic models for serialization and provides automatic
    cache invalidation and TTL management.
    """

    def __init__(
        self,
        config: CacheConfig | None = None,
        model_class: type[T] | None = None,
    ):
        self._config = config or CacheConfig()
        self._model_class = model_class
        self._l1 = get_cache()
        self._redis_client: redis.Redis | None = None

    @property
    def redis_client(self) -> redis.Redis | None:
        """Lazy Redis client initialization."""
        if self._redis_client is None and self._config.enable_redis:
            try:
                self._redis_client = RedisClientPool.get(self._config.redis_url).client
                self._redis_client.ping()
                logger.info("MultiLevelCache: Redis connected")
            except Exception as e:
                logger.warning(f"MultiLevelCache: Redis unavailable ({e})")
                self._redis_client = None
        return self._redis_client

    def _make_key(self, namespace: str, key: str) -> str:
        """Generate cache key with namespace."""
        return f"cache:{namespace}:{key}"

    def _serialize(self, data: Any) -> str:
        """Serialize data for storage."""
        if hasattr(data, "model_dump"):
            return json.dumps(data.model_dump(), ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False, default=str)

    def _deserialize(self, data: str, model_class: type[T] | None = None) -> Any:
        """Deserialize data from storage."""
        if not data:
            return None
        try:
            obj = json.loads(data)
            cls = model_class or self._model_class
            if cls and hasattr(cls, "model_validate"):
                return cls.model_validate(obj)
            return obj
        except (json.JSONDecodeError, TypeError):
            return data

    def _hash_key(self, key: str) -> str:
        """Hash long keys to avoid Redis key length issues."""
        if len(key) > 200:
            return hashlib.md5(key.encode()).hexdigest()
        return key

    def get(self, namespace: str, key: str) -> T | None:
        """Get value from cache, checking L1 then L2."""
        cache_key = self._make_key(namespace, self._hash_key(key))

        if self._config.enable_memory:
            hit = self._l1.get(cache_key)
            if hit is not None:
                return hit

        if self.redis_client:
            try:
                data = self.redis_client.get(cache_key)
                if data:
                    result = self._deserialize(data)
                    if self._config.enable_memory and result is not None:
                        self._l1.set(cache_key, result, ttl=min(self._config.default_ttl, 60))
                    return result
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        return None

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache (L1 + L2)."""
        cache_key = self._make_key(namespace, self._hash_key(key))
        ttl = ttl or self._config.default_ttl
        serialized = self._serialize(value)

        if self._config.enable_memory:
            self._l1.set(cache_key, value, ttl=min(ttl, 60))

        if self.redis_client:
            try:
                self.redis_client.setex(cache_key, ttl, serialized)
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        return False

    def delete(self, namespace: str, key: str) -> bool:
        """Delete key from all cache levels."""
        cache_key = self._make_key(namespace, self._hash_key(key))
        deleted = False

        if self._config.enable_memory:
            if self._l1.get(cache_key) is not None:
                self._l1.delete(cache_key)
                deleted = True

        if self.redis_client:
            try:
                if self.redis_client.delete(cache_key):
                    deleted = True
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")

        return deleted

    def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all keys in a namespace."""
        count = 0
        pattern = f"cache:{namespace}:*"

        if self._config.enable_memory:
            prefix = f"cache:{namespace}:"
            before = self._l1.stats()["total_keys"]
            self._l1.invalidate_pattern(prefix)
            after = self._l1.stats()["total_keys"]
            count += max(before - after, 0)

        if self.redis_client:
            try:
                count += delete_keys_by_pattern(self.redis_client, pattern)
            except Exception as e:
                logger.warning(f"Redis invalidate error: {e}")

        return count

    def get_or_set(
        self,
        namespace: str,
        key: str,
        factory: callable,
        ttl: int | None = None,
    ) -> T:
        """Get from cache or set using factory function."""
        coalesce_key = f"{namespace}:{key}"

        def _get() -> T | None:
            return self.get(namespace, key)

        def _set(value: T) -> None:
            if value is not None:
                self.set(namespace, key, value, ttl)

        return get_or_set_coalesced(coalesce_key, get_value=_get, set_value=_set, factory=factory)
