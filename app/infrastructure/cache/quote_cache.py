"""Redis Cache implementation for fast quote retrieval."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.infrastructure.cache.cache_manager import CacheManager, get_cache_manager

logger = get_logger(__name__)

_QUOTE_KEY_PREFIX = "quote:"


class QuoteCache:
    """Quote cache via unified CacheManager (L1 MemoryCache + L2 GlobalCache/Redis)."""

    def __init__(self, redis_url: str = ""):
        _ = redis_url  # GlobalCache resolves REDIS_URL; kept for constructor compatibility
        self.ttl = 60
        self._cache: CacheManager = get_cache_manager()

    def _quote_key(self, code: str) -> str:
        return f"{_QUOTE_KEY_PREFIX}{code}"

    def get_quotes(self, codes: list[str]) -> dict[str, Any]:
        """Fetch quotes from cache."""
        if not codes:
            return {}

        results: dict[str, Any] = {}
        for code in codes:
            hit = self._cache.get(self._quote_key(code))
            if hit is not None:
                results[code] = hit
        return results

    def set_quotes(self, quotes: dict[str, Any]) -> None:
        """Cache quotes."""
        if not quotes:
            return
        for code, data in quotes.items():
            self._cache.set(self._quote_key(code), data, ttl=self.ttl, memory_ttl=self.ttl)

    def clear_expired(self, max_age_seconds: int = 3600) -> int:
        """Clear expired quote entries. Redis handles TTL automatically, this is a no-op for compatibility."""
        return 0
