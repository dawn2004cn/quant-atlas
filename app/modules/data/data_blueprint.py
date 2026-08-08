"""Data Service — isolated blueprint for Phase 2G extraction.

This module creates a dedicated Flask Blueprint containing all data
routes. In Phase 2G, this blueprint can be mounted as a standalone
Flask app and eventually extracted into an independent microservice.

Current status: Monolithic (mounted under main Flask app)
Target status: Independent service (own Flask app, own DB connections)
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from app.core.registry import register_routes

# Create the data blueprint
data_bp = Blueprint("data_service", __name__)


def _register_data_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all data routes on the given blueprint.

    This function imports and registers all data route handlers.
    In Phase 2G, this becomes the entry point for the standalone service.

    Note: Some routes require specific services to be available in ctx.
    If a service is not available, that route group is skipped (logged as warning).
    """
    # Create minimal context stub if none provided
    if ctx is None:
        class _MinimalContext:
            enable_legacy_response_fields = False
            data_infrastructure_service = None
            data_lake_manager = None
            data_optimizer_service = None
            data_truth_guardian_service = None
            historical_resonance_service = None
            memory_optimization_service = None
            tdx_base_read_service = None
            qlib_pipeline_service = None
            task_pipeline_service = None
            market_service = None
            stock_service = None
        ctx = _MinimalContext()

    # Import route registration functions (side-effect: registers routes on blueprint)
    from app.presentation.api.routes_v1_data_infrastructure import (
        register_data_infrastructure_routes,
    )
    from app.presentation.api.routes_v1_data_lake import (
        register_data_lake_routes,
    )
    from app.presentation.api.routes_v1_data_optimizer import (
        register_data_optimizer_routes,
    )
    from app.presentation.api.routes_v1_data_verify import (
        register_data_verify_routes,
    )
    from app.presentation.api.routes_v1_historical_resonance import (
        register_historical_resonance_routes,
    )
    from app.presentation.api.routes_v1_qlib_rd import (
        register_qlib_rd_routes,
    )
    from app.presentation.api.routes_v1_pytdx import register_pytdx_routes

    import logging
    logger = logging.getLogger(__name__)

    # Register each route group, skipping if dependencies missing
    route_groups = [
        ("data_infrastructure", lambda: register_data_infrastructure_routes(blueprint, ctx)),
        ("data_lake", lambda: register_data_lake_routes(blueprint, ctx)),
        ("data_optimizer", lambda: register_data_optimizer_routes(blueprint, ctx)),
        ("data_verify", lambda: register_data_verify_routes(blueprint, ctx)),
        ("historical_resonance", lambda: register_historical_resonance_routes(blueprint, ctx)),
        ("qlib_rd", lambda: register_qlib_rd_routes(blueprint, ctx)),
        ("pytdx", lambda: register_pytdx_routes(blueprint, ctx)),
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
    name="data_service",
    context="data",
    description="Data Service (Phase 2G extraction target)",
)
def register_data_service_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all data routes on the main app blueprint.

    In Phase 2G, this will be replaced by:
        app = create_data_app()
        app.run(host="0.0.0.0", port=5701)
    """
    _register_data_routes(blueprint, ctx)


def create_data_blueprint(ctx: Any | None = None) -> tuple[Blueprint, list[str]]:
    """Create a standalone data blueprint.

    Args:
        ctx: ApiV1Context to pass to route handlers. If None, creates minimal fallback context.

    Returns:
        Tuple of (Blueprint, list of registered route group names).

    Usage (monolith):
        from app.modules.data.data_blueprint import data_bp
        app.register_blueprint(data_bp, url_prefix="/api/v1/data")

    Usage (Phase 2G standalone):
        from app.modules.data.data_blueprint import create_data_app
        app = create_data_app()
        app.run(port=5701)
    """
    bp = Blueprint("data_standalone", __name__)
    registered = _register_data_routes(bp, ctx)
    return bp, registered


def create_data_app() -> Any:
    """Create a standalone Flask app for Data Service (Phase 2G).

    This factory function creates a minimal Flask app containing only
    the data routes. In Phase 2G, this becomes the service entry point.

    Returns:
        Flask app instance (not yet running)
    """
    try:
        from flask import Flask

        app = Flask(__name__)

        # Initialize minimal extensions
        app.config["JSON_AS_ASCII"] = False
        app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64MB for data payloads

        # Register data routes
        bp, registered = create_data_blueprint()
        app.register_blueprint(bp, url_prefix="/api/v1/data")

        # Store registration info for debugging
        app.extensions["data_registered_routes"] = registered

        # Health check
        @app.route("/health")
        def health():
            return {"status": "ok", "service": "data", "version": "2g"}

        # Register with service discovery
        try:
            from app.core.service_discovery import register_service
            register_service(
                name="data",
                url="http://localhost:5701",
                health_path="/health",
                timeout=10.0,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Service discovery registration skipped: %s", exc)

        return app
    except ImportError:
        raise RuntimeError("Flask is required for data service")


__all__ = [
    "data_bp",
    "create_data_blueprint",
    "create_data_app",
    "register_data_service_routes",
]
