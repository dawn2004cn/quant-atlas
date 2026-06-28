"""Rate limiting with Redis when available and in-process fallback."""



from __future__ import annotations

import math
import time

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime

logger = get_logger(__name__)





class _MemoryRateLimiter:

    """Track attempts per key in-process."""



    def __init__(self, window: int = 60, max_attempts: int = 5) -> None:

        self.window = window

        self.max_attempts = max_attempts

        self._buckets: dict[str, list[float]] = {}



    def _prune(self, key: str, now: float) -> list[float]:

        bucket = self._buckets.setdefault(key, [])

        bucket[:] = [t for t in bucket if now - t < self.window]

        return bucket



    def is_blocked(self, key: str) -> bool:

        now = time.monotonic()

        return len(self._prune(key, now)) >= self.max_attempts



    def record(self, key: str) -> bool:

        """Record one attempt; return False if the key is now blocked."""

        now = time.monotonic()

        bucket = self._prune(key, now)

        if len(bucket) >= self.max_attempts:

            return False

        bucket.append(now)

        return True



    def retry_after(self, key: str) -> int:

        now = time.monotonic()

        bucket = self._prune(key, now)

        if len(bucket) < self.max_attempts:

            return 0

        oldest = min(bucket)

        return max(1, int(math.ceil(self.window - (now - oldest))))



    def reset(self, key: str) -> None:

        self._buckets.pop(key, None)



    def allow(self, key: str) -> bool:

        return self.record(key)





class HybridRateLimiter:

    """Redis fixed window when configured; otherwise in-memory sliding window."""



    def __init__(self, namespace: str, *, window: int = 60, max_attempts: int = 5) -> None:

        self._namespace = namespace

        self._window = window

        self._max_attempts = max_attempts

        self._memory = _MemoryRateLimiter(window=window, max_attempts=max_attempts)



    @property

    def window(self) -> int:

        return self._window



    def allow(self, key: str) -> bool:

        """Record one attempt and return whether it is still allowed."""

        redis_result = self._record_redis(key)

        if redis_result is not None:

            return redis_result

        return self._memory.record(key)



    def is_blocked(self, key: str) -> bool:

        redis_result = self._blocked_redis(key)

        if redis_result is not None:

            return redis_result

        return self._memory.is_blocked(key)



    def record(self, key: str) -> bool:

        return self.allow(key)



    def retry_after(self, key: str) -> int:

        redis_result = self._retry_after_redis(key)

        if redis_result is not None:

            return redis_result

        return self._memory.retry_after(key)



    def reset(self, key: str) -> None:
        self._memory.reset(key)
        url = self._redis_url()
        if not url:
            return
        try:
            self._redis_client().delete(self._redis_key(key))
        except Exception:
            logger.debug("Redis rate limit unavailable for %s", self._namespace, exc_info=True)



    def _redis_key(self, key: str) -> str:

        return f"ratelimit:{self._namespace}:{key}"



    def _redis_url(self) -> str:

        return (

            get_runtime("AUTH_RATE_LIMIT_REDIS_URL", "").strip()

            or get_runtime("TASK_MESSAGE_REDIS_URL", "").strip()

            or get_runtime("REDIS_URL", "").strip()

        )



    def _redis_client(self):

        from app.infrastructure.redis_client import RedisClientPool



        return RedisClientPool.get(self._redis_url()).client



    def _blocked_redis(self, key: str) -> bool | None:

        url = self._redis_url()

        if not url:

            return None

        try:

            client = self._redis_client()

            raw = client.get(self._redis_key(key))

            if raw is None:

                return False

            return int(raw) >= self._max_attempts

        except Exception:

            logger.debug("Redis rate limit unavailable for %s", self._namespace, exc_info=True)

            return None



    def _record_redis(self, key: str) -> bool | None:

        url = self._redis_url()

        if not url:

            return None

        try:

            client = self._redis_client()

            redis_key = self._redis_key(key)

            count = int(client.incr(redis_key))

            if count == 1:

                client.expire(redis_key, self._window)

            return count <= self._max_attempts

        except Exception:

            logger.debug("Redis rate limit unavailable for %s", self._namespace, exc_info=True)

            return None



    def _retry_after_redis(self, key: str) -> int | None:

        url = self._redis_url()

        if not url:

            return None

        try:

            client = self._redis_client()

            redis_key = self._redis_key(key)

            raw = client.get(redis_key)

            if raw is None or int(raw) < self._max_attempts:

                return 0

            ttl = int(client.ttl(redis_key))

            if ttl <= 0:

                return self._window

            return ttl

        except Exception:

            logger.debug("Redis rate limit unavailable for %s", self._namespace, exc_info=True)

            return None



    def _reset_redis(self, key: str) -> bool | None:

        url = self._redis_url()

        if not url:

            return None

        try:

            client = self._redis_client()

            client.delete(self._redis_key(key))

            return True

        except Exception:

            logger.debug("Redis rate limit unavailable for %s", self._namespace, exc_info=True)

            return None



    def _allow_redis(self, key: str) -> bool | None:

        """Backward-compatible alias used in tests."""

        return self._record_redis(key)

