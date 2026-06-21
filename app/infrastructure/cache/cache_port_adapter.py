from __future__ import annotations

"""Adapter that makes CacheManager satisfy the domain CachePort contract."""

from typing import Any, Callable

from app.domain.ports.cache_port import CachePort
from app.infrastructure.cache.cache_manager import CacheManager


class CacheManagerAdapter(CachePort):
    """Wraps the concrete CacheManager so it can be injected anywhere CachePort is expected."""

    def __init__(self, manager: CacheManager) -> None:
        self._mgr = manager

    def get(self, key: str, default: Any = None) -> Any:
        return self._mgr.get(key, default)

    def set(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        self._mgr.set(key, value, ttl=ttl)

    def delete(self, key: str) -> None:
        self._mgr.delete(key)

    def get_or_set(self, key: str, factory: Callable[[], Any], *, ttl: int | None = None) -> Any:
        return self._mgr.get_or_set(key, factory, ttl=ttl)

    def invalidate_prefix(self, prefix: str) -> int:
        return self._mgr.invalidate_prefix(prefix)
