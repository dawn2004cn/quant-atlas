from __future__ import annotations

from app.core.runtime_config import get_runtime

"""Redis-backed state repository for distributed singleton management.

This implements Single Source of Truth from quant_plan.md:
- Stores singleton state in Redis for multi-process consistency
- Implements distributed locks for atomic operations
- Supports state versioning and rollback
"""


import json
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import redis
from redis.lock import Lock

from app.core.logger import get_logger
from app.infrastructure.redis_client import RedisClientPool

logger = get_logger(__name__)


@dataclass
class StateVersion:
    """Versioned state snapshot."""
    version: int
    state: dict[str, Any]
    timestamp: str
    owner: str


class RedisStateRepository:
    """Redis-backed state repository for distributed environments.

    Solves "cognitive split" in multi-process deployments.
    """

    KEY_PREFIX = "state:singleton:"
    LOCK_PREFIX = "state:lock:"
    VERSION_KEY_SUFFIX = ":versions"

    MAX_VERSIONS = 10

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or get_runtime("REDIS_URL", "")
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = RedisClientPool.get(self._redis_url).client
        return self._client

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def get_state(self, singleton_name: str) -> dict[str, Any] | None:
        """Get current state of a singleton."""
        key = f"{self.KEY_PREFIX}{singleton_name}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None

    def set_state(
        self,
        singleton_name: str,
        state: dict[str, Any],
        owner: str = "system",
    ) -> bool:
        """Set state with atomic update and versioning."""
        key = f"{self.KEY_PREFIX}{singleton_name}"
        version_key = f"{key}{self.VERSION_KEY_SUFFIX}"

        pipe = self.client.pipeline()
        try:
            current = self.client.get(key)
            version = 1
            if current:
                current_data = json.loads(current)
                version = current_data.get("_version", 0) + 1

            state["_version"] = version
            state["_updated_at"] = datetime.now().isoformat()
            state["_owner"] = owner

            pipe.set(key, json.dumps(state))

            versions = self.client.lrange(version_key, 0, -1)
            versions_list = []
            if versions:
                versions_list = [json.loads(v) for v in versions]

            pipe.delete(version_key)
            for v in versions_list[-self.MAX_VERSIONS + 1:]:
                pipe.rpush(version_key, json.dumps(v))

            pipe.rpush(version_key, json.dumps(state))

            pipe.execute()
            logger.info(f"State updated: {singleton_name} v{version}")
            return True
        except Exception as e:
            logger.error(f"State update failed: {e}")
            return False

    def get_versions(self, singleton_name: str, limit: int = 5) -> list[StateVersion]:
        """Get version history."""
        key = f"{self.KEY_PREFIX}{singleton_name}{self.VERSION_KEY_SUFFIX}"
        versions_raw = self.client.lrange(key, 0, limit - 1)
        versions = []
        for v in versions_raw:
            data = json.loads(v)
            versions.append(StateVersion(
                version=data.get("_version", 0),
                state=data,
                timestamp=data.get("_updated_at", ""),
                owner=data.get("_owner", ""),
            ))
        return versions

    def rollback(self, singleton_name: str, target_version: int | None = None) -> bool:
        """Rollback to a previous version."""
        key = f"{self.KEY_PREFIX}{singleton_name}"

        if target_version is None:
            versions = self.get_versions(singleton_name, limit=2)
            if len(versions) < 2:
                return False
            target_version = versions[1].version

        version_key = f"{key}{self.VERSION_KEY_SUFFIX}"
        all_versions = self.client.lrange(version_key, 0, -1)

        for v in all_versions:
            data = json.loads(v)
            if data.get("_version") == target_version:
                state = {k: v for k, v in data.items() if not k.startswith("_")}
                return self.set_state(singleton_name, state)

        return False

    def acquire_lock(
        self,
        resource_name: str,
        owner: str,
        timeout_seconds: int = 30,
    ) -> Lock | None:
        """Acquire distributed lock for resource."""
        lock_key = f"{self.LOCK_PREFIX}{resource_name}"
        try:
            lock = self.client.lock(lock_key, timeout=timeout_seconds)
            if lock.acquire(blocking=True, blocking_timeout=5):
                logger.info(f"Lock acquired: {resource_name} by {owner}")
                return lock
        except Exception as e:
            logger.error(f"Lock acquisition failed: {e}")
        return None

    def release_lock(self, lock: Lock) -> bool:
        """Release distributed lock."""
        try:
            lock.release()
            return True
        except Exception as e:
            logger.error(f"Lock release failed: {e}")
            return False


_repository: RedisStateRepository | None = None
_local_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()


def get_state_repository() -> RedisStateRepository:
    """Get the global Redis state repository."""
    global _repository
    if _repository is None:
        _repository = RedisStateRepository()
    return _repository


class DistributedStateMixin:
    """Mixin to add Redis-backed state to singletons."""

    def get_distributed_state(self) -> dict[str, Any]:
        """Get state from Redis, fallback to local cache."""
        name = self.__class__.__name__
        repo = get_state_repository()
        state = repo.get_state(name)
        if state is not None:
            return state

        with _cache_lock:
            return _local_cache.get(name, {})

    def set_distributed_state(self, state: dict[str, Any], owner: str = "system") -> bool:
        """Set state to Redis with caching."""
        name = self.__class__.__name__
        repo = get_state_repository()

        with _cache_lock:
            _local_cache[name] = state

        return repo.set_state(name, state, owner)

    def sync_from_redis(self) -> bool:
        """Sync state from Redis to local."""
        name = self.__class__.__name__
        repo = get_state_repository()
        state = repo.get_state(name)
        if state:
            with _cache_lock:
                _local_cache[name] = state
            logger.info(f"Synced from Redis: {name}")
            return True
        return False
