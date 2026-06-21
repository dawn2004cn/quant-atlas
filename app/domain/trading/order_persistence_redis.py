"""Redis-backed order state persistence."""

from __future__ import annotations

import json
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime

logger = get_logger(__name__)

_ORDERS_HASH_KEY = "orders"


class RedisOrderPersistenceBackend:
    """Persist order state in a Redis hash."""

    def __init__(self, redis_url: str = "", client: Any | None = None) -> None:
        self._redis_url = redis_url.strip() or get_runtime("REDIS_URL", "")
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from app.infrastructure.redis_client import RedisClientPool

        return RedisClientPool.get(self._redis_url).binary_client

    def save_state(self, state: dict[str, Any]) -> bool:
        try:
            client = self._get_client()
            pipe = client.pipeline()
            for order_id, data in state.items():
                pipe.hset(_ORDERS_HASH_KEY, order_id, json.dumps(data, default=str))
            pipe.execute()
            return True
        except Exception as exc:
            logger.error("Redis save failed: %s", exc)
            return False

    def load_state(self) -> dict[str, Any]:
        try:
            client = self._get_client()
            raw = client.hgetall(_ORDERS_HASH_KEY)
            return {
                key.decode(): json.loads(value.decode())
                for key, value in raw.items()
            }
        except Exception as exc:
            logger.error("Redis load failed: %s", exc)
            return {}
