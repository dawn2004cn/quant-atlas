"""Portfolio/Risk Service — isolated blueprint for Phase 2D extraction.

This module creates a dedicated Flask Blueprint containing all portfolio
and risk routes. In Phase 2D, this blueprint can be mounted as a standalone
Flask app and eventually extracted into an independent microservice.

Current status: Monolithic (mounted under main Flask app)
Target status: Independent service (own Flask app, own DB connections)
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from app.core.registry import register_routes

# Create the portfolio/risk blueprint
portfolio_risk_bp = Blueprint("portfolio_risk_service", __name__)


def _register_portfolio_risk_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all portfolio/risk routes on the given blueprint.

    This function imports and registers all portfolio/risk route handlers.
    In Phase 2D, this becomes the entry point for the standalone service.

    Note: Some routes require specific services to be available in ctx.
    If a service is not available, that route group is skipped (logged as warning).
    """
    # Create minimal context stub if none provided
    if ctx is None:
        class _MinimalContext:
            enable_legacy_response_fields = False
            portfolio_service = None
            portfolio_trade_service = None
            risk_service = None
            risk_companion_service = None
            trade_plan_service = None
            signal_observation_service = None
            market_service = None
            stock_service = None
            user_service = None
            watchlist_service = None
            user_audit_trail_service = None
            market = None
            user = None
        ctx = _MinimalContext()

    # Import route registration functions (side-effect: registers routes on blueprint)
    from app.presentation.api.routes_v1_portfolio import (
        register_portfolio_routes,
    )
    from app.presentation.api.routes_v1_portfolio_users import (
        register_portfolio_user_routes,
    )
    from app.presentation.api.routes_v1_risk import (
        register_risk_routes,
    )
    from app.presentation.api.routes_v1_risk_companion import (
        register_risk_companion_routes,
    )
    from app.presentation.api.routes_v1_signal_observations import (
        register_signal_observation_routes,
    )
    from app.presentation.api.routes_v1_trade_plan import (
        register_trade_plan_routes,
    )

    import logging
    logger = logging.getLogger(__name__)

    # Register each route group, skipping if dependencies missing
    route_groups = [
        ("portfolio", lambda: register_portfolio_routes(blueprint, ctx)),
        ("portfolio_user", lambda: register_portfolio_user_routes(blueprint, ctx)),
        ("risk", lambda: register_risk_routes(blueprint, ctx)),
        ("risk_companion", lambda: register_risk_companion_routes(blueprint, ctx)),
        ("signal_observation", lambda: register_signal_observation_routes(blueprint, ctx)),
        ("trade_plan", lambda: register_trade_plan_routes(blueprint, ctx)),
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
    name="portfolio_risk_service",
    context="portfolio_risk",
    description="Portfolio/Risk Service (Phase 2D extraction target)",
)
def register_portfolio_risk_service_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all portfolio/risk routes on the main app blueprint.

    In Phase 2D, this will be replaced by:
        app = create_portfolio_risk_app()
        app.run(host="0.0.0.0", port=5401)
    """
    _register_portfolio_risk_routes(blueprint, ctx)


def create_portfolio_risk_blueprint() -> tuple[Blueprint, list[str]]:
    """Create a standalone portfolio/risk blueprint.

    Returns:
        Tuple of (Blueprint, list of registered route group names).

    Usage (monolith):
        from app.modules.portfolio_risk.portfolio_risk_blueprint import portfolio_risk_bp
        app.register_blueprint(portfolio_risk_bp, url_prefix="/api/v1/portfolio-risk")

    Usage (Phase 2D standalone):
        from app.modules.portfolio_risk.portfolio_risk_blueprint import create_portfolio_risk_app
        app = create_portfolio_risk_app()
        app.run(port=5401)
    """
    bp = Blueprint("portfolio_risk_standalone", __name__)
    registered = _register_portfolio_risk_routes(bp)
    return bp, registered


def create_portfolio_risk_app() -> Any:
    """Create a standalone Flask app for Portfolio/Risk Service (Phase 2D).

    This factory function creates a minimal Flask app containing only
    the portfolio/risk routes. In Phase 2D, this becomes the service entry point.

    Returns:
        Flask app instance (not yet running)
    """
    try:
        from flask import Flask

        app = Flask(__name__)

        # Initialize minimal extensions
        app.config["JSON_AS_ASCII"] = False
        app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

        # Register portfolio/risk routes
        bp, registered = create_portfolio_risk_blueprint()
        app.register_blueprint(bp, url_prefix="/api/v1/portfolio-risk")

        # Store registration info for debugging
        app.extensions["portfolio_risk_registered_routes"] = registered

        # Health check
        @app.route("/health")
        def health():
            return {"status": "ok", "service": "portfolio-risk", "version": "2d"}

        # Register with service discovery
        try:
            from app.core.service_discovery import register_service
            register_service(
                name="portfolio_risk",
                url="http://localhost:5401",
                health_path="/health",
                timeout=10.0,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Service discovery registration skipped: %s", exc)

        return app
    except ImportError:
        raise RuntimeError("Flask is required for portfolio/risk service")


__all__ = [
    "portfolio_risk_bp",
    "create_portfolio_risk_blueprint",
    "create_portfolio_risk_app",
    "register_portfolio_risk_service_routes",
]
