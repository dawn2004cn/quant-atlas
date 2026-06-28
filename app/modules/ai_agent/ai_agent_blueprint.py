"""AI Agent Service — isolated blueprint for Phase 2C extraction.

This module creates a dedicated Flask Blueprint containing all AI agent
routes. In Phase 2C, this blueprint can be mounted as a standalone Flask
app and eventually extracted into an independent microservice.

Current status: Monolithic (mounted under main Flask app)
Target status: Independent service (own Flask app, own GPU/LLM connections)
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint

from app.core.registry import register_routes

# Create the AI agent blueprint
ai_agent_bp = Blueprint("ai_agent_service", __name__)


def _register_ai_agent_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all AI agent routes on the given blueprint.

    This function imports and registers all AI agent route handlers.
    In Phase 2C, this becomes the entry point for the standalone service.

    Note: Some routes require specific services to be available in ctx.
    If a service is not available, that route group is skipped (logged as warning).
    """
    # Create minimal context stub if none provided
    if ctx is None:
        class _MinimalContext:
            enable_legacy_response_fields = False
            ai_analysis_service = None
            ai_research_service = None
            ai_evidence_service = None
            ai_hedge_fund_service = None
            fingpt_application_service = None
            smart_daily_briefing_service = None
            chart_vision_agent_service = None
            jarvis_proactive_service = None
            jarvis_semantic_router_service = None
            prompt_evolution_service = None
            investment_committee_service = None
            ai_committee_selection_service = None
            market_service = None
            strategy_service = None
            prediction_service = None
            selection_source_service = None
            rdagent_run_service = None
            swarm_service = None
            stock_service = None
            analysis_service = None
            user_service = None
            command_service = None
            task_dispatcher = None
            task_message_store = None
            enable_qlib = False
            ai = None

        ctx = _MinimalContext()

    # Import route registration functions (side-effect: registers routes on blueprint)
    import logging

    from app.presentation.api.routes_v1_ai_agent import (
        register_ai_agent_routes,
    )
    from app.presentation.api.routes_v1_ai_committee_selection import (
        register_ai_committee_selection_routes,
    )
    from app.presentation.api.routes_v1_ai_evidence import (
        register_ai_evidence_routes,
    )
    from app.presentation.api.routes_v1_ai_hedge_fund import (
        register_ai_hedge_fund_routes,
    )
    from app.presentation.api.routes_v1_chart_vision import (
        register_chart_vision_routes,
    )
    from app.presentation.api.routes_v1_cognitive_mesh import (
        register_cognitive_mesh_routes,
    )
    from app.presentation.api.routes_v1_fingpt import (
        register_fingpt_routes,
    )
    from app.presentation.api.routes_v1_investment_committee import (
        register_investment_committee_routes,
    )
    from app.presentation.api.routes_v1_jarvis import (
        register_jarvis_routes,
    )
    from app.presentation.api.routes_v1_jarvis_feed import (
        register_jarvis_feed_routes,
    )
    from app.presentation.api.routes_v1_llm_config import (
        register_llm_config_routes,
    )
    from app.presentation.api.routes_v1_nl import (
        register_nl_routes,
    )
    from app.presentation.api.routes_v1_quant_ai import (
        register_quant_ai_routes,
    )
    from app.presentation.api.routes_v1_smart_briefing import (
        register_smart_briefing_routes,
    )
    logger = logging.getLogger(__name__)

    # Register each route group, skipping if dependencies missing
    route_groups = [
        ("ai_agent", lambda: register_ai_agent_routes(blueprint, ctx)),
        ("fingpt", lambda: register_fingpt_routes(blueprint, ctx)),
        ("ai_evidence", lambda: register_ai_evidence_routes(blueprint, ctx)),
        ("ai_hedge_fund", lambda: register_ai_hedge_fund_routes(blueprint, ctx)),
        ("ai_committee_selection", lambda: register_ai_committee_selection_routes(blueprint, ctx)),
        ("investment_committee", lambda: register_investment_committee_routes(blueprint, ctx)),
        ("quant_ai", lambda: register_quant_ai_routes(blueprint, ctx)),
        ("smart_briefing", lambda: register_smart_briefing_routes(blueprint, ctx)),
        ("chart_vision", lambda: register_chart_vision_routes(blueprint, ctx)),
        ("jarvis", lambda: register_jarvis_routes(blueprint, ctx)),
        ("jarvis_feed", lambda: register_jarvis_feed_routes(blueprint, ctx)),
        ("llm_config", lambda: register_llm_config_routes(blueprint, ctx)),
        ("nl", lambda: register_nl_routes(blueprint, ctx)),
        ("cognitive_mesh", lambda: register_cognitive_mesh_routes(blueprint, ctx)),
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
    name="ai_agent_service",
    context="ai_agent",
    description="AI Agent Service (Phase 2C extraction target)",
)
def register_ai_agent_service_routes(blueprint: Blueprint, ctx: Any | None = None) -> None:
    """Register all AI agent routes on the main app blueprint.

    In Phase 2C, this will be replaced by:
        app = create_ai_agent_app()
        app.run(host="0.0.0.0", port=5301)
    """
    _register_ai_agent_routes(blueprint, ctx)


def create_ai_agent_blueprint() -> tuple[Blueprint, list[str]]:
    """Create a standalone AI agent blueprint.

    Returns:
        Tuple of (Blueprint, list of registered route group names).

    Usage (monolith):
        from app.modules.ai_agent.ai_agent_blueprint import ai_agent_bp
        app.register_blueprint(ai_agent_bp, url_prefix="/api/v1/ai-agent")

    Usage (Phase 2C standalone):
        from app.modules.ai_agent.ai_agent_blueprint import create_ai_agent_app
        app = create_ai_agent_app()
        app.run(port=5301)
    """
    bp = Blueprint("ai_agent_standalone", __name__)
    registered = _register_ai_agent_routes(bp)
    return bp, registered


def create_ai_agent_app() -> Any:
    """Create a standalone Flask app for AI Agent Service (Phase 2C).

    This factory function creates a minimal Flask app containing only
    the AI agent routes. In Phase 2C, this becomes the service entry point.

    Returns:
        Flask app instance (not yet running)
    """
    try:
        from flask import Flask

        app = Flask(__name__)

        # Initialize minimal extensions
        app.config["JSON_AS_ASCII"] = False
        app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64MB for AI payloads

        # Register AI agent routes
        bp, registered = create_ai_agent_blueprint()
        app.register_blueprint(bp, url_prefix="/api/v1/ai-agent")

        # Store registration info for debugging
        app.extensions["ai_agent_registered_routes"] = registered

        # Health check
        @app.route("/health")
        def health():
            return {"status": "ok", "service": "ai-agent", "version": "2c"}

        # Register with service discovery
        try:
            from app.core.service_discovery import register_service
            register_service(
                name="ai_agent",
                url="http://localhost:5301",
                health_path="/health",
                timeout=15.0,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("Service discovery registration skipped: %s", exc)

        return app
    except ImportError:
        raise RuntimeError("Flask is required for AI agent service") from None


__all__ = [
    "ai_agent_bp",
    "create_ai_agent_blueprint",
    "create_ai_agent_app",
    "register_ai_agent_service_routes",
]
