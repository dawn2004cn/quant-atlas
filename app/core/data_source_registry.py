"""Semantic data source registry — metadata-driven data provider discovery.

Phase 7.1 — allows agents to discover data sources by semantic query
(``type="kline", scope="realtime"``) instead of hardcoded service calls.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DataSource:
    """A registered data provider with semantic metadata."""

    name: str
    type: str  # "kline", "quote", "fundamental", "news", "sector", "chip", "indicator"
    scope: str  # "realtime", "history", "batch"
    market: str = "CN"  # "CN", "HK", "US", "global"
    description: str = ""
    priority: int = 0
    provider: Callable[..., Any] | None = None
    tags: tuple[str, ...] = ()

    def matches(self, type: str | None = None, scope: str | None = None, market: str | None = None) -> bool:
        if type is not None and self.type != type:
            return False
        if scope is not None and self.scope != scope:
            return False
        if market is not None and self.market != market:
            return False
        return True


class DataSourceRegistry:
    """Thread-safe registry of data sources for agentic discovery."""

    def __init__(self) -> None:
        self._sources: dict[str, list[DataSource]] = {}  # type -> list
        self._lock = threading.Lock()

    def register(self, source: DataSource) -> None:
        with self._lock:
            self._sources.setdefault(source.type, []).append(source)
            self._sources[source.type].sort(key=lambda s: -s.priority)

    def find(
        self,
        type: str | None = None,
        scope: str | None = None,
        market: str | None = None,
    ) -> list[DataSource]:
        with self._lock:
            results: list[DataSource] = []
            if type is not None:
                for src in self._sources.get(type, []):
                    if src.matches(type=type, scope=scope, market=market):
                        results.append(src)
            else:
                for sources in self._sources.values():
                    for src in sources:
                        if src.matches(type=type, scope=scope, market=market):
                            results.append(src)
        return sorted(results, key=lambda s: -s.priority)

    def find_best(
        self,
        type: str,
        scope: str | None = None,
        market: str | None = None,
    ) -> DataSource | None:
        results = self.find(type=type, scope=scope, market=market)
        return results[0] if results else None

    def list_types(self) -> list[str]:
        with self._lock:
            return sorted(self._sources.keys())

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"total": sum(len(v) for v in self._sources.values()), "by_type": {k: len(v) for k, v in self._sources.items()}}


_registry: DataSourceRegistry | None = None
_registry_lock = threading.Lock()


def get_data_source_registry() -> DataSourceRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = DataSourceRegistry()
    return _registry


def reset_data_source_registry() -> None:
    global _registry
    with _registry_lock:
        _registry = None


def data_source(
    name: str | None = None,
    type: str = "",
    scope: str = "",
    market: str = "CN",
    description: str = "",
    priority: int = 0,
    tags: list[str] | None = None,
):
    """Decorator that registers a data provider as a discoverable data source.

    Usage::

        @data_source(type="kline", scope="realtime", market="CN", priority=90)
        def get_tencent_kline(ticker: str) -> dict:
            ...

        # Agent queries:
        source = get_data_source_registry().find_best(type="kline", scope="realtime")
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        src = DataSource(
            name=name or fn.__name__,
            type=type or "",
            scope=scope or "",
            market=market,
            description=description or fn.__doc__ or "",
            priority=priority,
            provider=fn,
            tags=tuple(tags or []),
        )
        get_data_source_registry().register(src)
        return fn

    return decorator


def find_data_source(type: str, *, scope: str | None = None, market: str | None = None) -> DataSource | None:
    """Convenience function for agentic data source discovery."""
    return get_data_source_registry().find_best(type=type, scope=scope, market=market)


__all__ = [
    "DataSource",
    "DataSourceRegistry",
    "DataSourceType",
    "get_data_source_registry",
    "reset_data_source_registry",
    "data_source",
    "find_data_source",
]
