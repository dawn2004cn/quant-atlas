from __future__ import annotations
"""Context module registration and discovery.

Exposes ``ContextModule``, ``register_module``, ``discover_modules``,
and related helpers.
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from collections.abc import Callable

logger = logging.getLogger(__name__)

# ── module registries ───────────────────────────────────────────────────

_module_registry: dict[str, ContextModule] = {}


@dataclass
class ContextModule:
    """Self-describing context module that groups related services and routes.

    A ContextModule represents a bounded context in the domain, such as
    "risk", "portfolio", or "ai_agent". It declares which services and
    routes belong to this context, enabling modular discovery and loading.

    Each module can carry a ``ModuleLocalMemory`` for namespace-isolated
    lesson/pattern storage (Phase 11).
    """

    name: str
    description: str = ""
    services: list[type] = field(default_factory=list)
    routes: list[Callable] = field(default_factory=list)
    config_keys: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    enabled: bool = True
    wire: Callable[..., Any] | None = None
    initialize: Callable[..., Any] | None = None
    check_health: Callable[[], dict[str, Any]] | None = None
    memory: Any = None  # ModuleLocalMemory instance, lazy-initialized

    def get_or_create_memory(self) -> Any:
        if self.memory is None:
            from app.core.mesh.module_local_memory import ModuleLocalMemory
            self.memory = ModuleLocalMemory(module_name=self.name)
        return self.memory

    def is_enabled(self, config: dict[str, Any] | None = None) -> bool:
        """Check if this module is enabled based on config."""
        if not self.enabled:
            return False
        if not self.config_keys or not config:
            return True
        return all(config.get(key, True) for key in self.config_keys)

    def get_route_names(self) -> list[str]:
        """Get names of all routes in this module."""
        names: list[str] = []
        for route_fn in self.routes:
            if isinstance(route_fn, str):
                names.append(route_fn)
                continue
            name = getattr(route_fn, "_route_name", None)
            if name is None and callable(route_fn):
                name = route_fn.__name__
            if name:
                names.append(str(name))
        return names

    def get_service_names(self) -> list[str]:
        """Get names of all services in this module."""
        return [
            getattr(svc, "_service_name", svc.__name__)
            for svc in self.services
        ]


def register_module(
    cls: type | None = None,
    *,
    name: str | None = None,
    description: str = "",
):
    """Decorator that registers a context module.

    Usage::

        @register_module(name="risk", description="Risk management")
        class RiskModule:
            services = [RiskService]
            routes = [register_risk_routes]
    """
    def _decorator(klass: type) -> type:
        module_name = name or klass.__name__

        # Extract module attributes
        services = getattr(klass, "services", [])
        routes = getattr(klass, "routes", [])
        config_keys = getattr(klass, "config_keys", [])
        depends_on = getattr(klass, "depends_on", [])
        enabled = getattr(klass, "enabled", True)
        wire_fn = getattr(klass, "wire", None)
        initialize_fn = getattr(klass, "initialize", None)

        _routes = routes
        _config_keys = config_keys
        _depends_on = depends_on

        def _auto_check_health() -> dict[str, Any]:
            return {
                "name": module_name,
                "status": "ok",
                "routes": len(_routes) if isinstance(_routes, (list, tuple)) else 0,
                "config_keys": _config_keys or [],
                "depends_on": _depends_on,
            }
        check_health_fn = getattr(klass, "check_health", _auto_check_health)

        module = ContextModule(
            name=module_name,
            description=description or klass.__doc__ or "",
            services=services,
            routes=routes,
            config_keys=config_keys,
            depends_on=depends_on,
            enabled=enabled,
            wire=wire_fn if callable(wire_fn) else None,
            initialize=initialize_fn if callable(initialize_fn) else None,
            check_health=check_health_fn if callable(check_health_fn) else _auto_check_health,
        )
        _module_registry[module_name] = module

        # Mark class as registered
        klass._module_name = module_name
        klass._module = module
        return klass

    if cls is not None:
        return _decorator(cls)
    return _decorator


def discover_modules(
    *,
    config: dict[str, Any] | None = None,
) -> list[ContextModule]:
    """Discover and return enabled context modules.

    Args:
        config: Configuration dict for checking module enablement

    Returns:
        List of enabled ContextModule instances, sorted by dependencies
    """
    config = config or {}
    enabled_modules = [
        m for m in _module_registry.values()
        if m.is_enabled(config)
    ]

    # Sort by dependencies
    return _topological_sort_modules(enabled_modules)


def _topological_sort_modules(modules: list[ContextModule]) -> list[ContextModule]:
    """Sort modules by their depends_on declarations."""
    module_map = {m.name: m for m in modules}
    visited: set[str] = set()
    sorted_modules: list[ContextModule] = []

    def visit(name: str) -> None:
        if name in visited or name not in module_map:
            return
        visited.add(name)
        for dep in module_map[name].depends_on:
            visit(dep)
        sorted_modules.append(module_map[name])

    for module in modules:
        visit(module.name)

    return sorted_modules


def check_all_modules_health(*, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run check_health() on all enabled modules and return aggregated results."""
    modules = discover_modules(config=config)
    results = {}
    for module in modules:
        try:
            if module.check_health is not None:
                result = module.check_health()
            else:
                result = {"name": module.name, "status": "ok"}
            results[module.name] = result
        except Exception as exc:
            results[module.name] = {"name": module.name, "status": "error", "error": str(exc)}
    return {
        "total": len(modules),
        "healthy": sum(1 for r in results.values() if r.get("status") == "ok"),
        "modules": results,
    }


def get_module(name: str) -> ContextModule | None:
    """Get a context module by name."""
    return _module_registry.get(name)


def list_modules() -> list[str]:
    """List all registered module names."""
    return list(_module_registry)


def context_module_manifest(*, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Manifest of ``@register_module`` context modules (Phase 2 registry)."""
    try:
        from app.presentation.api.context_modules import ensure_all_modules_loaded
        ensure_all_modules_loaded()
    except Exception as exc:
        logger.debug("context_module_manifest preload skipped: %s", exc)

    cfg = config or {}
    modules = discover_modules(config=cfg)
    return {
        "schema_version": "v2",
        "module_count": len(modules),
        "modules": [
            {
                "name": m.name,
                "description": m.description,
                "services": m.get_service_names(),
                "routes": m.get_route_names(),
                "depends_on": list(m.depends_on),
                "enabled": m.is_enabled(cfg),
            }
            for m in modules
        ],
    }


__all__ = [
    "ContextModule",
    "register_module",
    "discover_modules",
    "check_all_modules_health",
    "get_module",
    "list_modules",
    "context_module_manifest",
    "_module_registry",
]
