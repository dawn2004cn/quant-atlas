"""Market Data Service — isolated blueprint for Phase 2A extraction.

This module creates a dedicated Flask Blueprint containing all market data
routes. In Phase 2A, this blueprint can be mounted as a standalone Flask
app and eventually extracted into an independent microservice.

Current status: Monolithic (mounted under main Flask app)
Target status: Independent service (own Flask app, own DB connections)
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from app.core.registry import register_routes

# Create the market data blueprint
market_data_bp = Blueprint("market_data_service", __name__)


def _register_market_data_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all market data routes on the given blueprint.

    This function imports and registers all market data route handlers.
    In Phase 2A, this becomes the entry point for the standalone service.

    Note: Some routes require specific services to be available in ctx.
    If a service is not available, that route group is skipped (logged as warning).
    """
    # Create minimal context stub if none provided
    if ctx is None:
        class _MinimalContext:
            enable_legacy_response_fields = False
            basic_market_data_service = None
            fundamental_access = None
            market_service = None
            stock_service = None
            global_market_service = None
            tdx_base_read_service = None
            hot_sector_storage_service = None
            sentiment_radar_service = None
        ctx = _MinimalContext()

    # Import route registration functions (side-effect: registers routes on blueprint)
    import logging

    from app.presentation.api.routes_market_sentiment import (
        register_sentiment_routes,
    )
    from app.presentation.api.routes_v1_global_market import (
        register_global_market_routes,
    )
    from app.presentation.api.routes_v1_pytdx import register_pytdx_routes
    from app.presentation.api.routes_v1_tdx_base import (
        register_tdx_base_routes,
    )
    from app.presentation.api.v1.hot_sectors.list_routes import (
        register_hot_sector_list_routes,
    )
    from app.presentation.api.v1.stock.routes_market_data import (
        register_stock_market_data,
    )
    logger = logging.getLogger(__name__)

    # Register each route group, skipping if dependencies missing
    route_groups = [
        ("stock_market_data", lambda: register_stock_market_data(blueprint, ctx)),
        ("global_market", lambda: register_global_market_routes(blueprint, ctx)),
        ("sentiment", lambda: register_sentiment_routes(blueprint, ctx)),
        ("tdx_base", lambda: register_tdx_base_routes(blueprint, ctx)),
        ("hot_sectors", lambda: register_hot_sector_list_routes(blueprint, ctx)),
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
    name="market_data_service",
    context="market_data",
    description="Market Data Service (Phase 2A extraction target)",
)
def register_market_data_service_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all market data routes on the main app blueprint.

    In Phase 2A, this will be replaced by:
        app = create_market_data_service_app()
        app.run(host="0.0.0.0", port=5101)
    """
    _register_market_data_routes(blueprint, ctx)


def create_market_data_blueprint() -> Blueprint:
    """Create a standalone market data blueprint.

    Returns:
        Blueprint that can be registered on any Flask app or run standalone.

    Usage (monolith):
        from app.modules.market_data.market_data_blueprint import market_data_bp
        app.register_blueprint(market_data_bp, url_prefix="/api/v1/market")

    Usage (Phase 2A standalone):
        from app.modules.market_data.market_data_blueprint import create_market_data_app
        app = create_market_data_app()
        app.run(port=5101)
    """
    bp = Blueprint("market_data_standalone", __name__)
    registered = _register_market_data_routes(bp)
    return bp, registered


def create_market_data_app() -> Any:
    """Create a standalone Flask app for Market Data Service (Phase 2A).

    This factory function creates a minimal Flask app containing only
    the market data routes. In Phase 2A, this becomes the service entry point.

    Returns:
        Flask app instance (not yet running)
    """
    try:
        from flask import Flask

        app = Flask(__name__)

        # Initialize minimal extensions (CORS, logging, etc.)
        app.config["JSON_AS_ASCII"] = False
        app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

        # Register market data routes
        bp, registered = create_market_data_blueprint()
        app.register_blueprint(bp, url_prefix="/api/v1/market")

        # Store registration info for debugging
        app.extensions["market_data_registered_routes"] = registered

        # Health check
        @app.route("/health")
        def health():
            return {"status": "ok", "service": "market-data", "version": "2a"}

        # Register with service discovery
        try:
            from app.core.service_discovery import register_service
            register_service(
                name="market_data",
                url="http://localhost:5101",
                health_path="/health",
                timeout=10.0,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Service discovery registration skipped: %s", exc)

        return app
    except ImportError:
        raise RuntimeError("Flask is required for market data service") from None


__all__ = [
    "market_data_bp",
    "create_market_data_blueprint",
    "create_market_data_app",
    "register_market_data_service_routes",
]
