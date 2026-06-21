from __future__ import annotations

import logging
from typing import Any

import redis
from redis import Redis

logger = logging.getLogger(__name__)


class RedisClientPool:
    """Centralized Redis connection manager with connection pooling.

    Replaces ad-hoc ``redis.from_url()`` calls across the codebase.
    """

    _instances: dict[str, "RedisClientPool"] = {}
    _default_url: str = ""

    def __init__(self, url: str) -> None:
        self.url = url
        self._pool: redis.ConnectionPool | None = None
        self._client_decode: Redis | None = None
        self._client_binary: Redis | None = None

    @classmethod
    def get(cls, url: str | None = None) -> "RedisClientPool":
        """Get or create a RedisClientPool for the given URL."""
        resolved = url or cls._default_url
        if resolved not in cls._instances:
            cls._instances[resolved] = cls(resolved)
        return cls._instances[resolved]

    @property
    def pool(self) -> redis.ConnectionPool:
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                self.url,
                max_connections=50,
                socket_connect_timeout=3,
                socket_timeout=5,
                health_check_interval=30,
                retry_on_timeout=True,
            )
        return self._pool

    @property
    def client(self) -> Redis:
        """Redis client with ``decode_responses=True`` (string values)."""
        if self._client_decode is None:
            self._client_decode = Redis(
                connection_pool=self.pool,
                decode_responses=True,
            )
        return self._client_decode

    @property
    def binary_client(self) -> Redis:
        """Redis client with ``decode_responses=False`` (binary/pubsub)."""
        if self._client_binary is None:
            self._client_binary = Redis(
                connection_pool=self.pool,
                decode_responses=False,
            )
        return self._client_binary

    def health(self) -> bool:
        try:
            return self.client.ping()
        except Exception:
            return False

    @classmethod
    def set_default_url(cls, url: str) -> None:
        cls._default_url = url


def scan_keys(client: Redis, pattern: str, *, count: int = 500) -> list[str]:
    """Collect Redis keys matching *pattern* via SCAN (non-blocking)."""
    keys: list[str] = []
    cursor = 0
    while True:
        cursor, batch = client.scan(cursor=cursor, match=pattern, count=count)
        if batch:
            keys.extend(batch)
        if cursor == 0:
            break
    return keys


def delete_keys_by_pattern(client: Redis, pattern: str, *, scan_count: int = 500) -> int:
    """Delete all keys matching *pattern*; returns number deleted."""
    keys = scan_keys(client, pattern, count=scan_count)
    if not keys:
        return 0
    deleted = 0
    chunk = 500
    for i in range(0, len(keys), chunk):
        deleted += int(client.delete(*keys[i : i + chunk]) or 0)
    return deleted
