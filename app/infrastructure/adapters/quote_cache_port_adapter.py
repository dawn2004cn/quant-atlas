from __future__ import annotations

"""Infrastructure adapter for ``QuoteCachePort``."""

from typing import Any

from app.domain.ports.quote_cache_port import QuoteCachePort
from app.infrastructure.cache.quote_cache import QuoteCache


class QuoteCachePortAdapter(QuoteCachePort):
    def __init__(self, *, redis_url: str | None = None) -> None:
        self._cache = QuoteCache() if redis_url is None else QuoteCache(redis_url=redis_url)

    def get_quotes(self, codes: list[str]) -> dict[str, Any]:
        return self._cache.get_quotes(codes)

    def set_quotes(self, quotes: dict[str, Any]) -> None:
        self._cache.set_quotes(quotes)

    def clear_expired(self, max_age_seconds: int = 3600) -> int:
        return self._cache.clear_expired(max_age_seconds)
