"""NL Parser API Routes."""

from dataclasses import asdict

from flask import Blueprint, request

from app.application.errors import ExternalServiceError, ValidationError
from app.modules.ai_agent.services.nl_parser import AdvancedNLParser
from .common import ok_response
from app.core.registry import register_routes

# Parent blueprint already uses url_prefix ``/api/v1``; nest only the NL segment.
nl_bp = Blueprint("nl", __name__, url_prefix="/nl")


@nl_bp.route("/query", methods=["POST"])
def parse_query():
    """Parse natural language query."""
    data = request.get_json(silent=True) or {}
    query = str(data.get("query", "") or "").strip()
    if not query:
        raise ValidationError("query_required")
    try:
        parser = AdvancedNLParser()
        result = parser.parse(query)
        return ok_response(data={"result": asdict(result)})
    except ValidationError:
        raise
    except Exception as exc:
        raise ExternalServiceError(
            "nl_parse_failed",
            details={"reason": str(exc)},
        ) from exc


@register_routes(name="nl", context="ai_agent", description="Natural language query parser")
def register_nl_routes(blueprint, ctx=None):
    """Register NL parser routes."""
    blueprint.register_blueprint(nl_bp)
