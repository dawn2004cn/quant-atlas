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
    """Auto-discover and register routes from @register_routes registry.

    Strategy, ai_agent, portfolio_risk, execution, system, data, and research
    context routes are delegated to their respective blueprints
    (Phase 2B/2C/2D/2E/2F/2G extraction).
    All other contexts are registered here.

    Returns list of successfully registered route names.
    """
    registered = []
    for name, register_fn in discover_routes():
        entry = register_fn if hasattr(register_fn, "_route_context") else None
        ctx_name = getattr(entry, "_route_context", "") if entry else ""
        # Skip strategy routes — registered via strategy blueprint
        if ctx_name == "strategy":
            continue
        # Skip ai_agent routes — registered via ai_agent blueprint
        if ctx_name == "ai_agent":
            continue
        # Skip portfolio_risk routes — registered via portfolio_risk blueprint
        if ctx_name == "portfolio_risk":
            continue
        # Skip execution routes — registered via execution blueprint
        if ctx_name == "execution":
            continue
        # Skip system routes — registered via system blueprint
        if ctx_name == "system":
            continue
        # Skip data routes — registered via data blueprint
        if ctx_name == "data":
            continue
        # Skip research routes — registered via research blueprint
        if ctx_name == "research":
            continue
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
    if preloaded:
        logger.debug("Route registry preloaded from %d modules", preloaded)

    # Phase 1: Auto-discover routes registered via @register_routes
    auto_discovered = _discover_and_register_routes(blueprint, ctx)
    if auto_discovered:
        logger.info(
            "Auto-discovered %d routes: %s",
            len(auto_discovered),
            ", ".join(auto_discovered),
        )

    # Phase 2: Register strategy blueprint (Phase 2B extraction target)
    if "strategy_service" not in _registered_routes:
        try:
            from app.modules.strategy.strategy_blueprint import (
                create_strategy_blueprint,
            )
            strategy_bp, strategy_groups = create_strategy_blueprint()
            blueprint.register_blueprint(strategy_bp, url_prefix="/strategy")
            _registered_routes.add("strategy_service")
            logger.info(
                "Registered strategy blueprint with %d route groups: %s",
                len(strategy_groups),
                ", ".join(strategy_groups),
            )
        except Exception as exc:
            logger.error("Failed to register strategy blueprint: %s", exc)

    # Phase 2.5: Register AI agent blueprint (Phase 2C extraction target)
    if "ai_agent_service" not in _registered_routes:
        try:
            from app.modules.ai_agent.ai_agent_blueprint import (
                create_ai_agent_blueprint,
            )
            ai_agent_bp, ai_agent_groups = create_ai_agent_blueprint()
            blueprint.register_blueprint(ai_agent_bp, url_prefix="/ai-agent")
            _registered_routes.add("ai_agent_service")
            logger.info(
                "Registered AI agent blueprint with %d route groups: %s",
                len(ai_agent_groups),
                ", ".join(ai_agent_groups),
            )
        except Exception as exc:
            logger.error("Failed to register AI agent blueprint: %s", exc)

    # Phase 2.6: Register portfolio/risk blueprint (Phase 2D extraction target)
    if "portfolio_risk_service" not in _registered_routes:
        try:
            from app.modules.portfolio_risk.portfolio_risk_blueprint import (
                create_portfolio_risk_blueprint,
            )
            portfolio_risk_bp, portfolio_risk_groups = create_portfolio_risk_blueprint()
            blueprint.register_blueprint(portfolio_risk_bp, url_prefix="/portfolio-risk")
            _registered_routes.add("portfolio_risk_service")
            logger.info(
                "Registered portfolio/risk blueprint with %d route groups: %s",
                len(portfolio_risk_groups),
                ", ".join(portfolio_risk_groups),
            )
        except Exception as exc:
            logger.error("Failed to register portfolio/risk blueprint: %s", exc)

    # Phase 2.7: Register execution blueprint (Phase 2E extraction target)
    if "execution_service" not in _registered_routes:
        try:
            from app.modules.execution.execution_blueprint import (
                create_execution_blueprint,
            )
            execution_bp, execution_groups = create_execution_blueprint()
            blueprint.register_blueprint(execution_bp, url_prefix="/execution")
            _registered_routes.add("execution_service")
            logger.info(
                "Registered execution blueprint with %d route groups: %s",
                len(execution_groups),
                ", ".join(execution_groups),
            )
        except Exception as exc:
            logger.error("Failed to register execution blueprint: %s", exc)

    # Phase 2.8: Register system/user blueprint (Phase 2F extraction target)
    if "system_user_service" not in _registered_routes:
        try:
            from app.modules.system.system_blueprint import (
                create_system_user_blueprint,
            )
            system_user_bp, system_user_groups = create_system_user_blueprint()
            blueprint.register_blueprint(system_user_bp, url_prefix="/system")
            _registered_routes.add("system_user_service")
            logger.info(
                "Registered system/user blueprint with %d route groups: %s",
                len(system_user_groups),
                ", ".join(system_user_groups),
            )
        except Exception as exc:
            logger.error("Failed to register system/user blueprint: %s", exc)

    # Phase 2.9: Register data blueprint (Phase 2G extraction target)
    if "data_service" not in _registered_routes:
        try:
            from app.modules.data.data_blueprint import (
                create_data_blueprint,
            )
            data_bp, data_groups = create_data_blueprint()
            blueprint.register_blueprint(data_bp, url_prefix="/data")
            _registered_routes.add("data_service")
            logger.info(
                "Registered data blueprint with %d route groups: %s",
                len(data_groups),
                ", ".join(data_groups),
            )
        except Exception as exc:
            logger.error("Failed to register data blueprint: %s", exc)

    # Phase 2.10: Register research blueprint (Phase 2G extraction target)
    if "research_service" not in _registered_routes:
        try:
            from app.modules.research.research_blueprint import (
                create_research_blueprint,
            )
            research_bp, research_groups = create_research_blueprint()
            blueprint.register_blueprint(research_bp, url_prefix="/research")
            _registered_routes.add("research_service")
            logger.info(
                "Registered research blueprint with %d route groups: %s",
                len(research_groups),
                ", ".join(research_groups),
            )
        except Exception as exc:
            logger.error("Failed to register research blueprint: %s", exc)

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
