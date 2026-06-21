from __future__ import annotations
"""Route registration and discovery.

Exposes ``register_routes``, ``discover_routes``, and route registry helpers.
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── route registries ────────────────────────────────────────────────────

_route_registry: dict[str, dict[str, Any]] = {}


def register_routes(
    fn: Callable | None = None,
    *,
    name: str | None = None,
    context: str = "default",
    description: str = "",
    depends_on: list[str] | None = None,
    enabled_by: str | None = None,
):
    """Decorator that registers a route registration function.

    Can be used with or without arguments::

        @register_routes
        def register_foo_routes(blueprint, ctx): ...

        @register_routes(name="chart_vision", context="vision", description="Chart vision API")
        def register_chart_vision_routes(blueprint, ctx): ...

    Args:
        name: Route module name (defaults to function name)
        context: Domain context this route belongs to (e.g., "risk", "portfolio", "ai_agent")
        description: Human-readable description
        depends_on: List of service names this route requires
        enabled_by: Config key that enables/disables this route (e.g., "ENABLE_VISION")
    """
    def _decorator(func: Callable) -> Callable:
        route_name = name or func.__name__
        _route_registry[route_name] = {
            "function": func,
            "context": context,
            "description": description or func.__doc__ or "",
            "depends_on": list(depends_on or []),
            "enabled_by": enabled_by,
            "module": func.__module__,
        }
        # Mark function as registered for introspection
        func._route_name = route_name
        func._route_context = context
        return func

    if fn is not None:
        # Used as @register_routes (no parentheses)
        return _decorator(fn)

    # Used as @register_routes(...)
    return _decorator


def is_route_registered(name: str) -> bool:
    """Check whether a route module has been registered."""
    return name in _route_registry


def registered_route_names() -> list[str]:
    """Return all registered route module names."""
    return list(_route_registry)


def registered_routes_by_context() -> dict[str, list[str]]:
    """Group registered routes by their context."""
    by_context: dict[str, list[str]] = {}
    for name, entry in _route_registry.items():
        ctx = entry["context"]
        by_context.setdefault(ctx, []).append(name)
    return by_context


def clear_route_registry() -> None:
    """Clear all registered routes (used in tests)."""
    _route_registry.clear()


def discover_routes(
    *,
    context: str | None = None,
    config: dict[str, Any] | None = None,
) -> list[tuple[str, Callable]]:
    """Discover and return route registration functions.

    Args:
        context: Filter by context (e.g., "risk", "vision")
        config: Configuration dict for checking enabled_by flags

    Returns:
        List of (name, registration_function) tuples, sorted by dependencies
    """
    config = config or {}
    results: list[tuple[str, Callable]] = []

    for name, entry in _route_registry.items():
        # Filter by context
        if context and entry["context"] != context:
            continue

        # Check enabled_by flag
        enabled_by = entry.get("enabled_by")
        if enabled_by and not config.get(enabled_by, False):
            logger.debug("Route %s disabled by config key %s", name, enabled_by)
            continue

        results.append((name, entry["function"]))

    # Sort by dependencies (topological sort)
    return _topological_sort_routes(results)


def _topological_sort_routes(
    routes: list[tuple[str, Callable]],
) -> list[tuple[str, Callable]]:
    """Sort routes by their depends_on declarations."""
    route_map = {name: fn for name, fn in routes}
    visited: set[str] = set()
    sorted_routes: list[tuple[str, Callable]] = []

    def visit(name: str) -> None:
        if name in visited or name not in route_map:
            return
        visited.add(name)
        # Visit dependencies first
        entry = _route_registry.get(name, {})
        for dep in entry.get("depends_on", []):
            visit(dep)
        sorted_routes.append((name, route_map[name]))

    for name, _ in routes:
        visit(name)

    return sorted_routes


__all__ = [
    "register_routes",
    "discover_routes",
    "is_route_registered",
    "registered_route_names",
    "registered_routes_by_context",
    "clear_route_registry",
    "_route_registry",
]
