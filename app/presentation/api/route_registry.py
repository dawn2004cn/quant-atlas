from __future__ import annotations
"""Route Module Registry - Modular route registration.

This module provides a pattern for organizing routes into separate modules
while maintaining compatibility with the existing Flask blueprint system.
"""


from dataclasses import dataclass, field
from collections.abc import Callable

from flask import Blueprint


@dataclass
class RouteModule:
    """A logical grouping of related API routes."""

    name: str
    description: str
    blueprint: Blueprint
    register_fn: Callable[[Blueprint], None] | None = None
    use_cases: list[str] = field(default_factory=list)


class RouteRegistry:
    """Registry for managing route modules."""

    _modules: dict[str, RouteModule] = {}
    _blueprint_cache: dict[str, Blueprint] = {}

    @classmethod
    def register(cls, module: RouteModule) -> None:
        """Register a route module."""
        cls._modules[module.name] = module

    @classmethod
    def get_module(cls, name: str) -> RouteModule | None:
        """Get a registered module by name."""
        return cls._modules.get(name)

    @classmethod
    def get_all_modules(cls) -> dict[str, RouteModule]:
        """Get all registered modules."""
        return cls._modules.copy()

    @classmethod
    def list_modules(cls) -> list[str]:
        """List all registered module names."""
        return list(cls._modules.keys())


def create_route_module(
    name: str,
    description: str,
    url_prefix: str = "",
) -> tuple[Blueprint, RouteModule]:
    """Helper to create a new route module with blueprint."""
    blueprint = Blueprint(name, __name__, url_prefix=url_prefix)
    module = RouteModule(
        name=name,
        description=description,
        blueprint=blueprint,
    )
    RouteRegistry.register(module)
    return blueprint, module


def register_route_module(blueprint: Blueprint, module: RouteModule) -> Blueprint:
    """Register a route module to a blueprint."""
    if module.register_fn:
        module.register_fn(blueprint)
    return blueprint


# Common route decorators for consistency
def route_summary(description: str):
    """Decorator to add route summary for documentation."""
    def decorator(fn):
        fn._route_summary = description
        return fn
    return decorator


def route_deprecated(reason: str = "Use new endpoint"):
    """Decorator to mark route as deprecated."""
    def decorator(fn):
        fn._deprecated = reason
        return fn
    return decorator
