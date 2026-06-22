"""System/User Service — isolated blueprint for Phase 2F extraction.

This module creates a dedicated Flask Blueprint containing all system
and user routes. In Phase 2F, this blueprint can be mounted as a standalone
Flask app and eventually extracted into an independent microservice.

Current status: Monolithic (mounted under main Flask app)
Target status: Independent service (own Flask app, own DB connections)
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from app.core.registry import register_routes

# Create the system/user blueprint
system_user_bp = Blueprint("system_user_service", __name__)


def _register_system_user_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all system/user routes on the given blueprint.

    This function imports and registers all system/user route handlers.
    In Phase 2F, this becomes the entry point for the standalone service.

    Note: Some routes require specific services to be available in ctx.
    If a service is not available, that route group is skipped (logged as warning).
    """
    # Create minimal context stub if none provided
    if ctx is None:
        class _MinimalContext:
            enable_legacy_response_fields = False
            user_service = None
            rbac_service = None
            config_service = None
            decision_trace_service = None
            market_service = None
            stock_service = None
            portfolio_service = None
            task_message_store = None
            enable_celery = False
            enable_legacy_response_fields = False
        ctx = _MinimalContext()

    # Import route registration functions (side-effect: registers routes on blueprint)
    from app.presentation.api.routes_v1_system_health import (
        register_system_health_routes,
    )
    from app.presentation.api.routes_v1_auth_identity import (
        register_auth_identity_routes,
    )
    from app.presentation.api.routes_v1_user_profile import (
        register_user_profile_routes,
    )
    from app.presentation.api.routes_v1_user_lifecycle import (
        register_user_lifecycle_routes,
    )

    import logging
    logger = logging.getLogger(__name__)

    # Register each route group, skipping if dependencies missing
    route_groups = [
        ("system_health", lambda: register_system_health_routes(blueprint, ctx)),
        ("auth_identity", lambda: register_auth_identity_routes(blueprint, ctx)),
        ("user_profile", lambda: register_user_profile_routes(blueprint, ctx)),
        ("user_lifecycle", lambda: register_user_lifecycle_routes(blueprint, ctx)),
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
    name="system_user_service",
    context="system",
    description="System/User Service (Phase 2F extraction target)",
)
def register_system_user_service_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all system/user routes on the main app blueprint.

    In Phase 2F, this will be replaced by:
        app = create_system_user_app()
        app.run(host="0.0.0.0", port=5601)
    """
    _register_system_user_routes(blueprint, ctx)


def create_system_user_blueprint() -> tuple[Blueprint, list[str]]:
    """Create a standalone system/user blueprint.

    Returns:
        Tuple of (Blueprint, list of registered route group names).

    Usage (monolith):
        from app.modules.system.system_blueprint import system_user_bp
        app.register_blueprint(system_user_bp, url_prefix="/api/v1/system")

    Usage (Phase 2F standalone):
        from app.modules.system.system_blueprint import create_system_user_app
        app = create_system_user_app()
        app.run(port=5601)
    """
    bp = Blueprint("system_user_standalone", __name__)
    registered = _register_system_user_routes(bp)
    return bp, registered


def create_system_user_app() -> Any:
    """Create a standalone Flask app for System/User Service (Phase 2F).

    This factory function creates a minimal Flask app containing only
    the system/user routes. In Phase 2F, this becomes the service entry point.

    Returns:
        Flask app instance (not yet running)
    """
    try:
        from flask import Flask

        app = Flask(__name__)

        # Initialize minimal extensions
        app.config["JSON_AS_ASCII"] = False
        app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

        # Register system/user routes
        bp, registered = create_system_user_blueprint()
        app.register_blueprint(bp, url_prefix="/api/v1/system")

        # Store registration info for debugging
        app.extensions["system_user_registered_routes"] = registered

        # Health check
        @app.route("/health")
        def health():
            return {"status": "ok", "service": "system-user", "version": "2f"}

        return app
    except ImportError:
        raise RuntimeError("Flask is required for system/user service")


__all__ = [
    "system_user_bp",
    "create_system_user_blueprint",
    "create_system_user_app",
    "register_system_user_service_routes",
]
