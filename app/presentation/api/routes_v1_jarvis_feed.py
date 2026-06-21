"""Jarvis feed API — anomaly → recommendation feed."""

from __future__ import annotations

from flask import Blueprint

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.presentation.api.responses import success_response

logger = get_logger(__name__)

_jarvis_conn = None


def _get_jarvis_conn():
    global _jarvis_conn
    if _jarvis_conn is None:
        from app.modules.ai_agent.services.jarvis_neural_connection import JarvisNeuralConnection

        _jarvis_conn = JarvisNeuralConnection()
    return _jarvis_conn


def _register_jarvis_feed_routes(blueprint: Blueprint, ctx=None) -> None:
    _ = ctx
    jarvis_bp = Blueprint("jarvis_feed", __name__, url_prefix="/jarvis")

    @jarvis_bp.route("/feed", methods=["GET"])
    def jarvis_feed():
        """Get recent proactive suggestions from anomaly → recommendation pipeline."""
        suggestions = _get_jarvis_conn().get_recent(limit=20)
        return success_response(data={"suggestions": suggestions})

    @jarvis_bp.route("/feed/clear", methods=["POST"])
    def clear_jarvis_feed():
        """Clear all stored suggestions."""
        _get_jarvis_conn().clear()
        return success_response()

    blueprint.register_blueprint(jarvis_bp)


@register_routes(name="jarvis_feed", context="ai_agent", description="Jarvis proactive feed")
def register_jarvis_feed_routes(blueprint: Blueprint, ctx=None) -> None:
    _register_jarvis_feed_routes(blueprint, ctx)
