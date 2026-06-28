"""Strategy Service — isolated blueprint for Phase 2B extraction.

This module creates a dedicated Flask Blueprint containing all strategy
routes. In Phase 2B, this blueprint can be mounted as a standalone Flask
app and eventually extracted into an independent microservice.

Current status: Monolithic (mounted under main Flask app)
Target status: Independent service (own Flask app, own DB connections)
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from app.core.registry import register_routes

# Create the strategy blueprint
strategy_bp = Blueprint("strategy_service", __name__)


def _register_strategy_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all strategy routes on the given blueprint.

    This function imports and registers all strategy route handlers.
    In Phase 2B, this becomes the entry point for the standalone service.

    Note: Some routes require specific services to be available in ctx.
    If a service is not available, that route group is skipped (logged as warning).
    """
    # Create minimal context stub if none provided
    if ctx is None:
        class _MinimalContext:
            enable_legacy_response_fields = False
            recommendation_service = None
            strategy_recommendation_service = None
            factor_orthogonalization_service = None
            factor_self_correction_service = None
            strategy_optimization_service = None
            strategy_shadow_service = None
            strategy_copilot_service = None
            strategy_synthesizer_service = None
            signal_observation_service = None
            signal_flag_service = None
            market_service = None
            stock_service = None
            narrative_synthesis_service = None
            simulation_gateway_service = None
            daily_workbench_service = None
        ctx = _MinimalContext()

    # Import route registration functions (side-effect: registers routes on blueprint)
    from app.presentation.api.routes_v1_recommendations import (
        register_recommendation_routes,
    )
    from app.presentation.api.routes_v1_factor import (
        register_factor_routes,
    )
    from app.presentation.api.routes_v1_strategy_optimization import (
        register_strategy_optimization_routes,
    )
    from app.presentation.api.routes_v1_strategy_shadow import (
        register_strategy_shadow_routes,
    )
    from app.presentation.api.routes_v1_strategy_copilot import (
        register_strategy_copilot_routes,
    )
    from app.presentation.api.routes_v1_strategy_snapshots import (
        register_strategy_snapshot_routes,
    )
    from app.presentation.api.routes_v1_strategy_synthesis import (
        register_strategy_synthesis_routes,
    )
    from app.presentation.api.routes_v1_signal_flag import (
        register_signal_flag_routes,
    )
    from app.presentation.api.routes_v1_attribution import (
        register_attribution_routes,
    )
    from app.presentation.api.routes_v1_reviews import (
        register_review_routes,
    )
    from app.presentation.api.routes_v1_alpha_mining import (
        register_alpha_mining_routes,
    )
    from app.presentation.api.routes_v1_one_click import (
        register_one_click_routes,
    )
    from app.presentation.api.routes_v1_strategy_wizard import (
        register_strategy_wizard_routes,
    )
    from app.presentation.api.routes_v1_ten_kings import (
        register_ten_kings_routes,
    )
    from app.presentation.api.routes_v1_wisdom_mesh import (
        register_wisdom_mesh_routes,
    )

    import logging
    logger = logging.getLogger(__name__)

    # Register each route group, skipping if dependencies missing
    route_groups = [
        ("recommendations", lambda: register_recommendation_routes(blueprint, ctx)),
        ("factor", lambda: register_factor_routes(blueprint, ctx)),
        ("strategy_optimization", lambda: register_strategy_optimization_routes(blueprint, ctx)),
        ("strategy_shadow", lambda: register_strategy_shadow_routes(blueprint, ctx)),
        ("strategy_copilot", lambda: register_strategy_copilot_routes(blueprint, ctx)),
        ("strategy_snapshot", lambda: register_strategy_snapshot_routes(blueprint, ctx)),
        ("strategy_synthesis", lambda: register_strategy_synthesis_routes(blueprint, ctx)),
        ("signal_flag", lambda: register_signal_flag_routes(blueprint, ctx)),
        ("attribution", lambda: register_attribution_routes(blueprint, ctx)),
        ("review", lambda: register_review_routes(blueprint, ctx)),
        ("alpha_mining", lambda: register_alpha_mining_routes(blueprint, ctx)),
        ("one_click", lambda: register_one_click_routes(blueprint, ctx)),
        ("strategy_wizard", lambda: register_strategy_wizard_routes(blueprint, ctx)),
        ("ten_kings", lambda: register_ten_kings_routes(blueprint, ctx)),
        ("wisdom_mesh", lambda: register_wisdom_mesh_routes(blueprint, ctx)),
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
    name="strategy_service",
    context="strategy",
    description="Strategy Service (Phase 2B extraction target)",
)
def register_strategy_service_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all strategy routes on the main app blueprint.

    In Phase 2B, this will be replaced by:
        app = create_strategy_app()
        app.run(host="0.0.0.0", port=5201)
    """
    _register_strategy_routes(blueprint, ctx)


def create_strategy_blueprint() -> tuple[Blueprint, list[str]]:
    """Create a standalone strategy blueprint.

    Returns:
        Tuple of (Blueprint, list of registered route group names).

    Usage (monolith):
        from app.modules.strategy.strategy_blueprint import strategy_bp
        app.register_blueprint(strategy_bp, url_prefix="/api/v1/strategy")

    Usage (Phase 2B standalone):
        from app.modules.strategy.strategy_blueprint import create_strategy_app
        app = create_strategy_app()
        app.run(port=5201)
    """
    bp = Blueprint("strategy_standalone", __name__)
    registered = _register_strategy_routes(bp)
    return bp, registered


def create_strategy_app() -> Any:
    """Create a standalone Flask app for Strategy Service (Phase 2B).

    This factory function creates a minimal Flask app containing only
    the strategy routes. In Phase 2B, this becomes the service entry point.

    Returns:
        Flask app instance (not yet running)
    """
    try:
        from flask import Flask

        app = Flask(__name__)

        # Initialize minimal extensions
        app.config["JSON_AS_ASCII"] = False
        app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

        # Register strategy routes
        bp, registered = create_strategy_blueprint()
        app.register_blueprint(bp, url_prefix="/api/v1/strategy")

        # Store registration info for debugging
        app.extensions["strategy_registered_routes"] = registered

        # Health check
        @app.route("/health")
        def health():
            return {"status": "ok", "service": "strategy", "version": "2b"}

        # Register with service discovery
        try:
            from app.core.service_discovery import register_service
            register_service(
                name="strategy",
                url="http://localhost:5201",
                health_path="/health",
                timeout=10.0,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Service discovery registration skipped: %s", exc)

        return app
    except ImportError:
        raise RuntimeError("Flask is required for strategy service")


__all__ = [
    "strategy_bp",
    "create_strategy_blueprint",
    "create_strategy_app",
    "register_strategy_service_routes",
]
