"""NL Parser API Routes."""

from dataclasses import asdict

from flask import request

from app.application.errors import ExternalServiceError, ValidationError
from app.core.registry import register_routes
from app.modules.ai_agent.services.nl_parser import AdvancedNLParser

from .common import ok_response

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
    """Register NL parser routes (canonical + legacy frontend path)."""
    blueprint.add_url_rule("/nl/query", endpoint="nl_query", view_func=parse_query, methods=["POST"])
    blueprint.add_url_rule(
        "/nl-parser/query",
        endpoint="nl_parser_query",
        view_func=parse_query,
        methods=["POST"],
    )
