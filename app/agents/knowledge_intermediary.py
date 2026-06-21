from __future__ import annotations
"""Knowledge Intermediary - Evidence-Aware Cache for Tool Calls.

This module implements the Agent-Knowledge Intermediary from midify_plan10.md:
- ToolCallCache: Caches tool results in blackboard format
- EvidenceAwareToolWrapper: Wraps tools to check blackboard first
- Avoids redundant tool calls when data is already available

Usage:
    wrapper = EvidenceAwareToolWrapper(get_market_data)
    result = wrapper(symbol="600519", agent_name="TechnicalAgent")
    # Checks blackboard first; only calls tool if data not available
"""


import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

from .evidence_blackboard import (
    get_evidence_blackboard,
    EvidenceBlackboard,
    EvidenceType,
    EvidenceStrength,
)


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolCallCache:
    """Cache entry for tool calls."""
    tool_name: str
    arguments: dict[str, Any]
    result: Any
    timestamp: datetime
    ttl_seconds: int = 300

    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age < self.ttl_seconds


class EvidenceAwareCache:
    """Evidence-aware cache that integrates with blackboard.

    Instead of just caching tool results, this cache:
    1. Stores data in blackboard format for easy access
    2. Validates against existing blackboard entries
    3. Provides LRU eviction for memory efficiency
    """

    def __init__(self, max_entries: int = 1000):
        self._max_entries = max_entries
        self._cache: dict[str, ToolCallCache] = {}
        self._access_order: list[str] = []

    def _make_key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Generate cache key from tool name and arguments."""
        import hashlib
        import orjson as json

        arg_str = json.dumps(arguments, sort_keys=True)
        key_data = f"{tool_name}:{arg_str}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_or_compute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        compute_func: Callable,
        ttl_seconds: int = 300,
    ) -> tuple[Any, bool]:
        """Get cached result or compute new one.

        Returns:
            (result, was_cached)
        """
        key = self._make_key(tool_name, arguments)

        if key in self._cache:
            entry = self._cache[key]
            if entry.is_valid():
                self._update_access(key)
                logger.debug(f"Cache hit for {tool_name}")
                return entry.result, True
            else:
                del self._cache[key]
                self._access_order.remove(key)

        result = compute_func()

        self._cache[key] = ToolCallCache(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            timestamp=datetime.now(),
            ttl_seconds=ttl_seconds,
        )

        self._update_access(key)
        self._evict_if_needed()

        logger.debug(f"Cache miss for {tool_name}, computed new result")
        return result, False

    def _update_access(self, key: str) -> None:
        """Update access order for LRU."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache is full."""
        while len(self._cache) > self._max_entries:
            if self._access_order:
                oldest_key = self._access_order.pop(0)
                self._cache.pop(oldest_key, None)

    def invalidate(self, pattern: str | None = None) -> None:
        """Invalidate cache entries."""
        if pattern is None:
            self._cache.clear()
            self._access_order.clear()
            return

        keys_to_remove = [k for k in self._cache if pattern in k]
        for key in keys_to_remove:
            self._cache.pop(key, None)
            if key in self._access_order:
                self._access_order.remove(key)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        valid_entries = sum(1 for e in self._cache.values() if e.is_valid())
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "max_entries": self._max_entries,
        }


class EvidenceAwareToolWrapper:
    """Wrapper that adds evidence-aware caching to tool functions.

    This implements the core optimization: instead of each agent
    calling tools directly, we check if data exists in blackboard first.
    """

    def __init__(self, tool_func: Callable, tool_name: str | None = None):
        self._tool_func = tool_func
        self._tool_name = tool_name or getattr(tool_func, "__name__", "unknown")
        self._cache = EvidenceAwareCache()

    def __call__(self, agent_name: str, *args, **kwargs) -> Any:
        """Execute tool with evidence-aware caching.

        Checks:
        1. If data already exists in blackboard -> return from there
        2. Else check cache -> return if valid
        3. Else call tool and cache result
        """
        bb = get_evidence_blackboard()

        data_key = kwargs.get("symbol") or kwargs.get("stock_code") or kwargs.get("code")

        if data_key:
            existing = bb.read_value(agent_name, f"data_{data_key}")
            if existing is not None:
                logger.info(f"Data for {data_key} found in blackboard by {agent_name}")
                return existing

        cached_result, was_cached = self._cache.get_or_compute(
            self._tool_name,
            kwargs,
            lambda: self._tool_func(*args, **kwargs),
        )

        if data_key and not was_cached:
            bb.write(
                agent_name=agent_name,
                key=f"data_{data_key}",
                value=cached_result,
                evidence_type=EvidenceType.QUANTITATIVE,
                strength=EvidenceStrength.MODERATE,
                narrative=f"Retrieved via {self._tool_name}",
            )

        return cached_result


def wrap_tool_with_evidence_awareness(tool_func: Callable) -> EvidenceAwareToolWrapper:
    """Decorator to wrap a tool function with evidence-aware caching."""
    return EvidenceAwareToolWrapper(tool_func)


_global_tool_cache = EvidenceAwareCache()


def get_tool_cache() -> EvidenceAwareCache:
    """Get the global tool cache."""
    return _global_tool_cache