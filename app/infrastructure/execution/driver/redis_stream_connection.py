from __future__ import annotations

"""Redis Stream 连接与 consumer group 生命周期。"""

import logging
import time

import redis

from app.infrastructure.redis_client import RedisClientPool

logger = logging.getLogger(__name__)


class RedisStreamConnection:
    """Lazy Redis client + consumer group for stream-based executors."""

    def __init__(self, redis_url: str, queue_name: str) -> None:
        self._redis_url = redis_url
        self._queue_name = queue_name
        self._client: redis.Redis | None = None
        self._consumer_group = f"executor_{int(time.time())}"

    @property
    def redis_url(self) -> str:
        return self._redis_url

    @property
    def consumer_group(self) -> str:
        return self._consumer_group

    @property
    def queue_name(self) -> str:
        return self._queue_name

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = RedisClientPool.get(self._redis_url).client
        return self._client

    def ping(self) -> bool:
        self.client.ping()
        return True

    def ensure_consumer_group(self) -> None:
        try:
            self.client.xgroup_create(
                self._queue_name,
                self._consumer_group,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
            logger.info("Consumer group %s already exists", self._consumer_group)
