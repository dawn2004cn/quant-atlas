"""Research Service — isolated blueprint for Phase 2G extraction.

This module creates a dedicated Flask Blueprint containing all research
routes. In Phase 2G, this blueprint can be mounted as a standalone
Flask app and eventually extracted into an independent microservice.

Current status: Monolithic (mounted under main Flask app)
Target status: Independent service (own Flask app, own DB connections)
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from app.core.registry import register_routes

# Create the research blueprint
research_bp = Blueprint("research_service", __name__)


def _register_research_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all research routes on the given blueprint.

    This function imports and registers all research route handlers.
    In Phase 2G, this becomes the entry point for the standalone service.

    Note: Some routes require specific services to be available in ctx.
    If a service is not available, that route group is skipped (logged as warning).
    """
    # Create minimal context stub if none provided
    if ctx is None:
        class _MinimalContext:
            enable_legacy_response_fields = False
            swarm_agent_service = None
            swarm_arbiter_service = None
            decision_replay_space_service = None
            decision_theater_service = None
            evidence_graph_service = None
            simulation_gateway_service = None
            swarm_topology_service = None
            workflow_service = None
            market_service = None
            stock_service = None
        ctx = _MinimalContext()

    # Import route registration functions (side-effect: registers routes on blueprint)
    from app.presentation.api.routes_v1_agent_swarm import (
        register_agent_swarm_routes,
    )
    from app.presentation.api.routes_v1_decision_replay import (
        register_decision_replay_routes,
    )
    from app.presentation.api.routes_v1_decision_theater import (
        register_decision_theater_routes,
    )
    from app.presentation.api.routes_v1_evidence_graph import (
        register_evidence_routes,
    )
    from app.presentation.api.routes_v1_simulation import (
        register_simulation_routes,
    )
    from app.presentation.api.routes_v1_swarm_topology import (
        register_swarm_topology_routes,
    )
    from app.presentation.api.routes_v1_workflows import (
        register_workflow_routes,
    )

    import logging
    logger = logging.getLogger(__name__)

    # Register each route group, skipping if dependencies missing
    route_groups = [
        ("agent_swarm", lambda: register_agent_swarm_routes(blueprint, ctx)),
        ("decision_replay", lambda: register_decision_replay_routes(blueprint, ctx)),
        ("decision_theater", lambda: register_decision_theater_routes(blueprint, ctx)),
        ("evidence_graph", lambda: register_evidence_routes(blueprint, ctx)),
        ("simulation", lambda: register_simulation_routes(blueprint, ctx)),
        ("swarm_topology", lambda: register_swarm_topology_routes(blueprint, ctx)),
        ("workflow", lambda: register_workflow_routes(blueprint, ctx)),
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
    name="research_service",
    context="research",
    description="Research Service (Phase 2G extraction target)",
)
def register_research_service_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all research routes on the main app blueprint.

    In Phase 2G, this will be replaced by:
        app = create_research_app()
        app.run(host="0.0.0.0", port=5801)
    """
    _register_research_routes(blueprint, ctx)


def create_research_blueprint() -> tuple[Blueprint, list[str]]:
    """Create a standalone research blueprint.

    Returns:
        Tuple of (Blueprint, list of registered route group names).

    Usage (monolith):
        from app.modules.research.research_blueprint import research_bp
        app.register_blueprint(research_bp, url_prefix="/api/v1/research")

    Usage (Phase 2G standalone):
        from app.modules.research.research_blueprint import create_research_app
        app = create_research_app()
        app.run(port=5801)
    """
    bp = Blueprint("research_standalone", __name__)
    registered = _register_research_routes(bp)
    return bp, registered


def create_research_app() -> Any:
    """Create a standalone Flask app for Research Service (Phase 2G).

    This factory function creates a minimal Flask app containing only
    the research routes. In Phase 2G, this becomes the service entry point.

    Returns:
        Flask app instance (not yet running)
    """
    try:
        from flask import Flask

        app = Flask(__name__)

        # Initialize minimal extensions
        app.config["JSON_AS_ASCII"] = False
        app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

        # Register research routes
        bp, registered = create_research_blueprint()
        app.register_blueprint(bp, url_prefix="/api/v1/research")

        # Store registration info for debugging
        app.extensions["research_registered_routes"] = registered

        # Health check
        @app.route("/health")
        def health():
            return {"status": "ok", "service": "research", "version": "2g"}

        # Register with service discovery
        try:
            from app.core.service_discovery import register_service
            register_service(
                name="research",
                url="http://localhost:5801",
                health_path="/health",
                timeout=10.0,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Service discovery registration skipped: %s", exc)

        return app
    except ImportError:
        raise RuntimeError("Flask is required for research service")


__all__ = [
    "research_bp",
    "create_research_blueprint",
    "create_research_app",
    "register_research_service_routes",
]
