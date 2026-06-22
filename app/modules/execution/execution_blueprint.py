"""Execution Service — isolated blueprint for Phase 2E extraction.

This module creates a dedicated Flask Blueprint containing all execution
routes. In Phase 2E, this blueprint can be mounted as a standalone Flask
app and eventually extracted into an independent microservice.

Current status: Monolithic (mounted under main Flask app)
Target status: Independent service (own Flask app, own DB connections)
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from app.core.registry import register_routes

# Create the execution blueprint
execution_bp = Blueprint("execution_service", __name__)


def _register_execution_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all execution routes on the given blueprint.

    This function imports and registers all execution route handlers.
    In Phase 2E, this becomes the entry point for the standalone service.

    Note: Some routes require specific services to be available in ctx.
    If a service is not available, that route group is skipped (logged as warning).
    """
    # Create minimal context stub if none provided
    if ctx is None:
        class _MinimalContext:
            enable_legacy_response_fields = False
            trade_execution_pipeline_service = None
            self_healing_execution_service = None
            simulation_gateway_service = None
            borderless_execution_service = None
            market_service = None
            stock_service = None
            portfolio_service = None
            user_service = None
        ctx = _MinimalContext()

    # Import route registration functions (side-effect: registers routes on blueprint)
    from app.presentation.api.routes_v1_execution import (
        register_execution_routes,
    )
    from app.presentation.api.routes_v1_self_healing_execution import (
        register_self_healing_execution_routes,
    )

    import logging
    logger = logging.getLogger(__name__)

    # Register each route group, skipping if dependencies missing
    route_groups = [
        ("execution", lambda: register_execution_routes(blueprint, ctx)),
        ("self_healing_execution", lambda: register_self_healing_execution_routes(blueprint, ctx)),
    ]

    registered = []
    for name, register_fn in route_groups:
        try:
            register_fn()
            registered.append(name)
            logger.debug("Registered route group: %s", name)
        except Exception as exc:
            logger.warning("Skipping route group %s (dependencies unavailable): %s", name, exc)

    return registered


@register_routes(
    name="execution_service",
    context="execution",
    description="Execution Service (Phase 2E extraction target)",
)
def register_execution_service_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all execution routes on the main app blueprint.

    In Phase 2E, this will be replaced by:
        app = create_execution_app()
        app.run(host="0.0.0.0", port=5501)
    """
    _register_execution_routes(blueprint, ctx)


def create_execution_blueprint() -> tuple[Blueprint, list[str]]:
    """Create a standalone execution blueprint.

    Returns:
        Tuple of (Blueprint, list of registered route group names).

    Usage (monolith):
        from app.modules.execution.execution_blueprint import execution_bp
        app.register_blueprint(execution_bp, url_prefix="/api/v1/execution")

    Usage (Phase 2E standalone):
        from app.modules.execution.execution_blueprint import create_execution_app
        app = create_execution_app()
        app.run(port=5501)
    """
    bp = Blueprint("execution_standalone", __name__)
    registered = _register_execution_routes(bp)
    return bp, registered


def create_execution_app() -> Any:
    """Create a standalone Flask app for Execution Service (Phase 2E).

    This factory function creates a minimal Flask app containing only
    the execution routes. In Phase 2E, this becomes the service entry point.

    Returns:
        Flask app instance (not yet running)
    """
    try:
        from flask import Flask

        app = Flask(__name__)

        # Initialize minimal extensions
        app.config["JSON_AS_ASCII"] = False
        app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

        # Register execution routes
        bp, registered = create_execution_blueprint()
        app.register_blueprint(bp, url_prefix="/api/v1/execution")

        # Store registration info for debugging
        app.extensions["execution_registered_routes"] = registered

        # Health check
        @app.route("/health")
        def health():
            return {"status": "ok", "service": "execution", "version": "2e"}

        # Register with service discovery
        try:
            from app.core.service_discovery import register_service
            register_service(
                name="execution",
                url="http://localhost:5501",
                health_path="/health",
                timeout=10.0,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Service discovery registration skipped: %s", exc)

        return app
    except ImportError:
        raise RuntimeError("Flask is required for execution service")


__all__ = [
    "execution_bp",
    "create_execution_blueprint",
    "create_execution_app",
    "register_execution_service_routes",
]
