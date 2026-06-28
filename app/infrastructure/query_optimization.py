from __future__ import annotations

"""Query Optimization for Batch Operations.

Supports efficient batch queries with connection reuse.
"""


from dataclasses import dataclass
from typing import TypeVar

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class QueryResult:
    """Query result wrapper."""
    data: list
    count: int
    cached: bool = False


class BatchQueryExecutor:
    """Executes optimized batch queries."""

    def __init__(self, cache_ttl: int = 60):
        self._cache: dict = {}
        self._cache_ttl = cache_ttl
        self._query_count = 0
        self._cache_hits = 0
        logger.info(f"BatchQueryExecutor initialized: ttl={cache_ttl}s")

    def execute(
        self,
        query_fn,
        keys: list,
        **kwargs
    ) -> list:
        """Execute batch query with caching."""
        self._query_count += 1

        # Check cache
        cache_key = str(keys)
        if cache_key in self._cache:
            self._cache_hits += 1
            logger.debug(f"Cache hit: {len(keys)} keys")
            return self._cache[cache_key]

        # Execute batch
        result = query_fn(keys, **kwargs)

        # Cache result
        self._cache[cache_key] = result

        return result

    def invalidate(self, key: str = None) -> None:
        """Invalidate cache."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    def get_stats(self) -> dict:
        """Get query stats."""
        hit_rate = (
            self._cache_hits / self._query_count * 100
            if self._query_count > 0 else 0
        )
        return {
            "query_count": self._query_count,
            "cache_hits": self._cache_hits,
            "hit_rate": f"{hit_rate:.1f}%",
            "cached_keys": len(self._cache)
        }


# Global instance
_batch_query_executor: BatchQueryExecutor = None


def get_batch_query_executor() -> BatchQueryExecutor:
    """Get global batch query executor."""
    global _batch_query_executor
    if _batch_query_executor is None:
        _batch_query_executor = BatchQueryExecutor(cache_ttl=60)
    return _batch_query_executor


__all__ = [
    "QueryResult",
    "BatchQueryExecutor",
    "get_batch_query_executor",
]
