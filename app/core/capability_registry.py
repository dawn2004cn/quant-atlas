"""Semantic capability registry for AI Agent dynamic tool discovery.

Phase 5.1 — allows services to advertise *what they can do* (not just
what they are), enabling agents to find the right tool by natural-language
query instead of hardcoded references.

Usage::

    @register_capability(
        name="get_market_kline",
        description="查询A股5分钟K线数据",
        domain="market_data",
        tags=["market", "kline"],
    )
    def get_market_kline(ticker: str, period: str = "5m") -> dict: ...

    # Agent queries
    registry = get_capability_registry()
    results = registry.search("K线数据")
    fn = registry.resolve("get_market_kline")
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Capability:
    """A registered capability descriptor."""

    name: str
    description: str
    domain: str = ""
    tags: tuple[str, ...] = ()
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    handler: Callable[..., Any] | None = None
    priority: int = 0

    def matches_query(self, query: str) -> float:
        """Simple relevance scoring: substring match in description + tags."""
        q = query.lower()
        score = 0.0
        if q in self.description.lower():
            score += 2.0
        if q in self.name.lower():
            score += 1.5
        for tag in self.tags:
            if q in tag.lower():
                score += 1.0
        if q in self.domain.lower():
            score += 0.5
        return score


class CapabilityRegistry:
    """Thread-safe registry of capabilities for semantic discovery."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._lock = threading.Lock()

    def register(self, cap: Capability) -> None:
        with self._lock:
            if cap.name in self._capabilities:
                logger.debug("Capability %s overwritten", cap.name)
            self._capabilities[cap.name] = cap

    def get(self, name: str) -> Capability | None:
        with self._lock:
            return self._capabilities.get(name)

    def resolve(self, name: str) -> Callable[..., Any] | None:
        cap = self.get(name)
        return cap.handler if cap is not None else None

    def search(self, query: str, *, limit: int = 10) -> list[Capability]:
        """Find capabilities matching a natural-language query."""
        with self._lock:
            caps = list(self._capabilities.values())
        scored = [(cap.matches_query(query), cap) for cap in caps]
        scored.sort(key=lambda x: (-x[0], -x[1].priority))
        return [cap for score, cap in scored if score > 0][:limit]

    def list_all(self) -> list[Capability]:
        with self._lock:
            return list(self._capabilities.values())

    def list_by_domain(self, domain: str) -> list[Capability]:
        with self._lock:
            return [c for c in self._capabilities.values() if c.domain == domain]

    def to_agent_tools(self, *, domains: list[str] | None = None) -> list[dict[str, Any]]:
        """Export capabilities as OpenAI function-calling schemas."""
        caps = self.list_by_domain(domains[0]) if domains and len(domains) == 1 else self.list_all()
        if domains:
            domain_set = set(domains)
            caps = [c for c in caps if c.domain in domain_set]
        return [
            {
                "type": "function",
                "function": {
                    "name": cap.name,
                    "description": cap.description,
                    "parameters": cap.input_schema or {"type": "object", "properties": {}},
                },
            }
            for cap in caps
        ]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            domains = {}
            for cap in self._capabilities.values():
                domains[cap.domain] = domains.get(cap.domain, 0) + 1
            return {
                "total": len(self._capabilities),
                "by_domain": domains,
            }


# ── global singleton ──────────────────────────────────────────────────────

_registry: CapabilityRegistry | None = None
_registry_lock = threading.Lock()


def get_capability_registry() -> CapabilityRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = CapabilityRegistry()
    return _registry


def reset_capability_registry() -> None:
    global _registry
    with _registry_lock:
        _registry = None


# ── decorator ─────────────────────────────────────────────────────────────


def register_capability(
    name: str | None = None,
    description: str = "",
    domain: str = "",
    tags: list[str] | None = None,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
    priority: int = 0,
):
    """Decorator that registers a function as a discoverable capability.

    Can decorate a function or a method::

        @register_capability(
            name="get_kline",
            description="查询A股K线数据",
            domain="market_data",
            tags=["kline", "realtime"],
        )
        def get_kline(ticker: str) -> dict: ...
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        cap_name = name or fn.__name__
        cap = Capability(
            name=cap_name,
            description=description or fn.__doc__ or "",
            domain=domain,
            tags=tuple(tags or []),
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            handler=fn,
            priority=priority,
        )
        get_capability_registry().register(cap)
        return fn

    return decorator


__all__ = [
    "Capability",
    "CapabilityRegistry",
    "get_capability_registry",
    "reset_capability_registry",
    "register_capability",
]
