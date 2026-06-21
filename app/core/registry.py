"""Backward-compat re-exports for the unified registry modules.

Existing code importing from ``app.core.registry`` continues to work.
New code should import from the specific submodule.

Unified registry:
    - Service registration → ``app.core.typed_registry``
    - Route registration → ``app.core.route_registry``
    - Module discovery → ``app.core.module_registry``
    - Bootstrap bridge → ``app.bootstrap_components.service_wiring``
"""

from __future__ import annotations

from app.core.typed_registry import (
    ServiceRegistry,
    register_factory,
    register_service,
    get_registry,
    registered_service_names,
)
from app.core.route_registry import (
    _route_registry,
    clear_route_registry,
    discover_routes,
    is_route_registered,
    register_routes,
    registered_route_names,
    registered_routes_by_context,
)
from app.core.module_registry import (
    ContextModule,
    _module_registry,
    check_all_modules_health,
    context_module_manifest,
    discover_modules,
    get_module,
    list_modules,
    register_module,
)
from app.core.registry_bootstrap import (
    configure_service_registry,
    rewire_infra_dependent_services,
    wire_from_registry,
)

__all__ = [
    # Service registry (legacy, see typed_registry.py)
    "register_service",
    "register_factory",
    "ServiceRegistry",
    "get_registry",
    "registered_service_names",
    # Route registry
    "register_routes",
    "discover_routes",
    "is_route_registered",
    "registered_route_names",
    "registered_routes_by_context",
    "clear_route_registry",
    "_route_registry",
    # Module registry
    "ContextModule",
    "register_module",
    "discover_modules",
    "check_all_modules_health",
    "get_module",
    "list_modules",
    "context_module_manifest",
    "_module_registry",
    # Bootstrap
    "configure_service_registry",
    "wire_from_registry",
    "rewire_infra_dependent_services",
]
