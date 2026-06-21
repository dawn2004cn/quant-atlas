"""Service group facade registry — logical grouping without moving files.

Provides a single entrypoint for grouped service imports,
preserving backward compatibility with existing absolute imports.
"""
from __future__ import annotations

from typing import Any


class ServiceGroupFacadeRegistry:
    """Registry mapping group names to their re-export modules."""

    _groups: dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, module: Any) -> None:
        cls._groups[name] = module

    @classmethod
    def get(cls, name: str) -> Any | None:
        return cls._groups.get(name)

    @classmethod
    def list_groups(cls) -> list[str]:
        return list(cls._groups.keys())


def _register_default_groups() -> None:
    # Note: 'ops', 'admin', 'infrastructure', 'vision' subdirs were
    # removed in Phase 17 as they contained only re-export stubs.
    # Remaining subdirs with real code: ai, analytics, orchestration,
    # strategy, ui, immune, data, helpers, execution, factor, mesh,
    # monitoring, portfolio, qlib, research, research_ops, risk,
    # scanner, sentinel, strategies, system, tools, trading, user
    from app.application.services import (
        ai,
        analytics,
        integration,
        research,
        system,
        trading,
        user,
    )
    ServiceGroupFacadeRegistry.register("trading", trading)
    ServiceGroupFacadeRegistry.register("research", research)
    ServiceGroupFacadeRegistry.register("ai", ai)
    ServiceGroupFacadeRegistry.register("analytics", analytics)
    ServiceGroupFacadeRegistry.register("system", system)
    ServiceGroupFacadeRegistry.register("user", user)
    ServiceGroupFacadeRegistry.register("integration", integration)
