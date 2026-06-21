"""API v1: Registry introspection routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from ...core.registry import register_routes
from .common import ok_response
from .v1_context import ApiV1Context


@register_routes(name="registry", context="system", description="Registry introspection")
def register_registry_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register registry introspection routes."""
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/registry/routes")
    @login_required
    def registry_routes():
        """List all registered routes with their context and metadata."""
        from ...core.registry import (
            discover_routes,
            registered_route_names,
            registered_routes_by_context,
            _route_registry,
        )

        context_filter = (request.args.get("context") or "").strip() or None

        routes_by_ctx = registered_routes_by_context()
        if context_filter:
            routes_by_ctx = {k: v for k, v in routes_by_ctx.items() if k == context_filter}

        route_details = []
        for name in registered_route_names():
            entry = _route_registry.get(name, {})
            route_details.append({
                "name": name,
                "context": entry.get("context", "unknown"),
                "description": entry.get("description", ""),
                "module": entry.get("module", ""),
                "depends_on": entry.get("depends_on", []),
                "enabled_by": entry.get("enabled_by"),
            })

        if context_filter:
            route_details = [r for r in route_details if r["context"] == context_filter]

        return ok_response(
            data={
                "total": len(route_details),
                "by_context": routes_by_ctx,
                "routes": route_details,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/registry/services")
    @login_required
    def registry_services():
        """List all registered services with their metadata."""
        from ...core.registry import (
            registered_service_names,
            is_service_registered,
            _registry,
        )

        service_details = []
        for name in registered_service_names():
            entry = _registry.get(name, {})
            service_details.append({
                "name": name,
                "class": entry.get("class", {}).__name__ if entry.get("class") else None,
                "scope": entry.get("scope", "singleton"),
                "depends": [d.__name__ if hasattr(d, "__name__") else str(d) for d in entry.get("depends", [])],
                "enabled_by": entry.get("enabled_by"),
                "lazy": entry.get("lazy", False),
                "has_factory": entry.get("factory") is not None,
            })

        return ok_response(
            data={
                "total": len(service_details),
                "services": service_details,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/registry/modules")
    @login_required
    def registry_modules():
        """List all registered context modules."""
        from . import context_modules as _ctx_mods
        from ...core.registry import list_modules, get_module

        module_details = []
        for name in list_modules():
            module = get_module(name)
            if module:
                module_details.append({
                    "name": module.name,
                    "description": module.description,
                    "routes": module.get_route_names(),
                    "services": module.get_service_names(),
                    "config_keys": module.config_keys,
                    "depends_on": module.depends_on,
                    "enabled": module.enabled,
                })

        return ok_response(
            data={
                "total": len(module_details),
                "modules": module_details,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/registry/summary")
    @login_required
    def registry_summary():
        """High-level summary of the declarative registry."""
        from ...core.registry import (
            registered_service_names,
            registered_route_names,
            registered_routes_by_context,
            list_modules,
        )
        from . import context_modules as _ctx_mods

        routes_by_ctx = registered_routes_by_context()

        return ok_response(
            data={
                "services": len(registered_service_names()),
                "routes": len(registered_route_names()),
                "contexts": len(routes_by_ctx),
                "modules": len(list_modules()),
                "route_contexts": {k: len(v) for k, v in routes_by_ctx.items()},
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    blueprint.register_blueprint(Blueprint("_registry_dummy", __name__))
