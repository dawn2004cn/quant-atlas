"""REST API blueprint with declarative route discovery.

All standard v1 route modules use ``@register_routes`` for automatic
discovery.  Non-standard signatures (e.g. ``admin_stock_cache``) are
registered in ``create_api_blueprint`` after the auto-discovery pass.

New routes should use @register_routes for automatic discovery.
"""

from __future__ import annotations

import logging

from flask import Blueprint

from app.core.registry import discover_routes

from .route_loader import preload_route_modules
from .route_contract import (
    finalize_v1_route_contract,
    preload_critical_route_modules,
    repair_unregistered_critical_modules,
)
from .v1_context import create_api_v1_context

logger = logging.getLogger(__name__)

def _is_strict_bootstrap() -> bool:
    """Determine if we're in strict bootstrap mode.

    Delegates to ``service_readiness.is_strict_bootstrap()`` which
    detects production/staging via ``FLASK_ENV``/``APP_ENV``.
    """
    from app.bootstrap_components.service_readiness import is_strict_bootstrap as _is_strict

    return _is_strict()


# Track which routes have been registered to avoid duplicates
_registered_routes: set[str] = set()


def _register_route_safe(
    name: str,
    register_fn,
    blueprint: Blueprint,
    ctx,
) -> bool:
    """Register a route if not already registered.

    Returns True if the route was registered, False if skipped.
    In strict bootstrap mode (STRICT_BOOTSTRAP=1), registration failures
    raise RuntimeError instead of silently swallowing the error.
    """
    if name in _registered_routes:
        logger.debug("Route %s already registered, skipping", name)
        return False
    try:
        register_fn(blueprint, ctx)
        _registered_routes.add(name)
        return True
    except Exception as exc:
        if _is_strict_bootstrap():
            raise RuntimeError(
                f"Route registration failed for {name}: {exc}"
            ) from exc
        logger.error(
            "Failed to register route %s: %s (file=%s, line=%s)",
            name, exc, exc.__traceback__.tb_frame.f_code.co_filename,
            exc.__traceback__.tb_lineno,
        )
        return False


def _discover_and_register_routes(blueprint: Blueprint, ctx) -> list[str]:
    """Auto-discover and register all @register_routes handlers on the main v1 blueprint.

    Context-tagged routes (system, data, ai_agent, …) use canonical paths such as
    ``/api/v1/jarvis/proactive`` and ``/api/v1/data/timeseries-health``. Sub-blueprint
    prefixes previously produced 404s (e.g. ``/api/v1/ai-agent/jarvis/...``) or double
    segments (``/api/v1/system/system/...``).

    Returns list of successfully registered route names.
    """
    registered = []
    for name, register_fn in discover_routes():
        if _register_route_safe(name, register_fn, blueprint, ctx):
            registered.append(name)
            logger.debug("Auto-discovered route: %s", name)
    return registered


def _register_all_routes(blueprint: Blueprint, ctx) -> None:
    """Register all API v1 routes using auto-discovery.

    Registration order:
    0. Preload route modules (populate @register_routes registry)
    1. Auto-discovered routes (from @register_routes decorator)
    """
    preloaded = preload_route_modules()
    preload_critical_route_modules()
    if preloaded:
        logger.debug("Route registry preloaded from %d modules", preloaded)

    # Phase 1: Auto-discover routes registered via @register_routes
    auto_discovered = _discover_and_register_routes(blueprint, ctx)

    # Phase 1b: Ensure critical frontend paths even if discovery/preload skipped a module
    repair_unregistered_critical_modules(blueprint, ctx, _registered_routes)
    if auto_discovered:
        logger.info(
            "Auto-discovered %d routes: %s",
            len(auto_discovered),
            ", ".join(auto_discovered),
        )

    # Phase 2 (context sub-blueprints) removed: all @register_routes handlers mount on
    # the main /api/v1 blueprint above. Standalone blueprints remain in modules/* for
    # future microservice extraction but are not double-mounted in the monolith.

    # Phase 3: Register journey catalog routes (non-conflicting /journeys namespace)
    if "journeys" not in _registered_routes:
        from .routes_v1_journeys import register_journey_routes
        register_journey_routes(blueprint, ctx)
        _registered_routes.add("journeys")

    logger.info(
        "Total routes registered: %d (auto: %d)",
        len(_registered_routes),
        len(auto_discovered),
    )


def create_api_blueprint(
    api_bundle,
    task_dispatcher,
    task_message_store,
    enable_celery: bool = False,
    enable_legacy_response_fields: bool = False,
    *,
    enable_qlib: bool = False,
    enable_rd_agent: bool = False,
):
    """Create the API v1 blueprint with all routes registered.

    Routes are registered in two phases:
    1. Auto-discovered routes (from @register_routes decorator)
    2. Legacy routes (manual imports, for backward compatibility)

    Special cases:
    - register_admin_stock_cache_routes has a different signature
    """
    global _registered_routes
    _registered_routes = set()

    blueprint = Blueprint("api_v1", __name__, url_prefix="/api/v1")
    from app.presentation.strategic_sunset_hooks import attach_api_sunset_guard

    attach_api_sunset_guard(blueprint)
    ctx = create_api_v1_context(
        api_bundle,
        task_dispatcher=task_dispatcher,
        task_message_store=task_message_store,
        enable_celery=enable_celery,
        enable_legacy_response_fields=enable_legacy_response_fields,
        enable_qlib=enable_qlib,
        enable_rd_agent=enable_rd_agent,
    )

    # Register all routes (auto-discovered + legacy fallback)
    _register_all_routes(blueprint, ctx)

    # Special case: admin_stock_cache_routes has a different signature
    if "admin_stock_cache" not in _registered_routes:
        from .routes_v1_admin_stocks import register_admin_stock_cache_routes
        register_admin_stock_cache_routes(
            blueprint, enable_legacy_response_fields=enable_legacy_response_fields
        )
        _registered_routes.add("admin_stock_cache")

    return blueprint


def apply_v1_route_contract(app, *, strict: bool | None = None) -> list[str]:
    """Run after ``app.register_blueprint(api_v1)`` — audit paths + legacy aliases."""
    return finalize_v1_route_contract(app, strict=strict)
