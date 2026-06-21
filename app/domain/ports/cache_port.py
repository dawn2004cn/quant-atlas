from __future__ import annotations

"""Domain port for generic application caching (L1+L2).

Provides a thin abstraction over CacheManager so that application-layer
services can be constructed without reaching into infrastructure.
"""

from typing import Any, Callable, Protocol


class CachePort(Protocol):
    """Generic cache contract used by application services."""

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the cache."""
        ...

    def set(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        """Store a value in the cache."""
        ...

    def delete(self, key: str) -> None:
        """Remove a value from the cache."""
        ...

    def get_or_set(self, key: str, factory: Callable[[], Any], *, ttl: int | None = None) -> Any:
        """Atomically retrieve or compute+store a cached value."""
        ...

    def invalidate_prefix(self, prefix: str) -> int:
        """Delete all keys matching a prefix pattern. Returns count."""
        ...


class _NoOpCachePort:
    """No-op cache port for environments without Redis/memory cache."""

    def get(self, key: str, default: Any = None) -> Any:
        return default

    def set(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        pass

    def delete(self, key: str) -> None:
        pass

    def get_or_set(self, key: str, factory: Callable[[], Any], *, ttl: int | None = None) -> Any:
        return factory()

    def invalidate_prefix(self, prefix: str) -> int:
        return 0


def get_no_op_cache() -> CachePort:
    """Return a no-op cache port when caching is unavailable."""
    return _NoOpCachePort()
