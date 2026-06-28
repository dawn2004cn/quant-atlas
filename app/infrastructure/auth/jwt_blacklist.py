"""JWT token blacklist for immediate revocation on logout / security events.

Phase 5 Enhancement: Blacklist support using Redis (primary) or in-memory set
(fallback) so tokens can be rejected before their natural expiry.
"""

from __future__ import annotations

import time
import threading

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime

logger = get_logger(__name__)


class _InMemoryBlacklist:
    """Thread-safe in-memory blacklist for development / single-process use."""

    def __init__(self) -> None:
        self._blacklist: dict[str, float] = {}
        self._lock = threading.Lock()

    def add(self, jti: str, expires_at: float) -> None:
        with self._lock:
            self._blacklist[jti] = expires_at

    def check(self, jti: str) -> bool:
        with self._lock:
            expires_at = self._blacklist.get(jti)
            if expires_at is None:
                return False
            if time.time() > expires_at:
                del self._blacklist[jti]
                return False
            return True

    def cleanup(self) -> int:
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._blacklist.items() if v <= now]
            for k in expired:
                del self._blacklist[k]
        logger.debug("JWT blacklist cleanup: removed %d expired entries", len(expired))
        return len(expired)


class _RedisBlacklist:
    """Redis-backed blacklist using SET with TTL per entry."""

    def __init__(self, redis_url: str) -> None:
        import redis as _r
        self._redis = _r.from_url(redis_url)
        self._prefix = "jwt:blacklist:"

    def add(self, jti: str, expires_at: float) -> None:
        ttl = max(1, int(expires_at - time.time()))
        self._redis.setex(f"{self._prefix}{jti}", ttl, str(expires_at))

    def check(self, jti: str) -> bool:
        return self._redis.exists(f"{self._prefix}{jti}") > 0

    def cleanup(self) -> int:
        # Redis auto-expires entries; no manual cleanup needed
        return 0


# Singleton
_blacklist: _InMemoryBlacklist | _RedisBlacklist | None = None


def _get_blacklist():
    global _blacklist
    if _blacklist is not None:
        return _blacklist
    redis_url = get_runtime("REDIS_URL", "")
    if redis_url:
        try:
            _blacklist = _RedisBlacklist(redis_url)
            logger.info("JWT blacklist: using Redis backend (%s)", redis_url)
            return _blacklist
        except Exception as exc:
            logger.warning("Redis unavailable for JWT blacklist, fallback to memory: %s", exc)
    _blacklist = _InMemoryBlacklist()
    logger.info("JWT blacklist: using in-memory backend")
    return _blacklist


def revoke_token(jti: str, expires_at: float) -> None:
    """Add a token to the blacklist by its JTI."""
    _get_blacklist().add(jti, expires_at)
    logger.info("JWT token revoked: jti=%s", jti[:8])


def is_token_revoked(jti: str) -> bool:
    """Check if a token has been revoked."""
    return _get_blacklist().check(jti)
