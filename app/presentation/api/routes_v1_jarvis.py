"""API v1: Jarvis command orb, semantic routing, and command plan."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from .common import ok_response
from .decorators import service_fallback
from .v1_context import ApiV1Context


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="jarvis", context="system", description="Jarvis command orb")
def register_jarvis_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register Jarvis and command plan routes."""
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/jarvis/proactive")
    @login_required
    @service_fallback("jarvis_proactive_service")
    def jarvis_proactive():
        """Jarvis 5.0 — proactive watchlist opportunity scan."""
        svc = getattr(ctx, "jarvis_proactive_service", None)
        payload = svc.scan(_uid())
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/system/ask")
    @login_required
    @service_fallback("jarvis_semantic_router_service")
    def system_ask():
        """Jarvis 7.0 — semantic intent routing for command orb (label + url)."""
        svc = getattr(ctx, "jarvis_semantic_router_service", None)
        q = (request.args.get("q") or "").strip()
        if not q:
            raise ValidationError("query_required")
        payload = svc.route(_uid(), q)
        if not payload.input_snapshot.get("ok"):
            raise ValidationError(
                payload.input_snapshot.get("error") or "ask_failed",
                details=payload.input_snapshot,
            )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/jarvis/semantic-route")
    @login_required
    @service_fallback("jarvis_semantic_router_service")
    def jarvis_semantic_route():
        """Full semantic routing with pattern-match candidates."""
        svc = getattr(ctx, "jarvis_semantic_router_service", None)
        req_body = request.get_json(silent=True) or {}
        q = (req_body.get("query") or req_body.get("command") or request.args.get("q") or "").strip()
        if not q:
            raise ValidationError("query_required")
        payload = svc.route(_uid(), q)
        if not payload.input_snapshot.get("ok"):
            raise ValidationError(
                payload.input_snapshot.get("error") or "route_failed",
                details=payload.input_snapshot,
            )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/jarvis/winning-patterns")
    @login_required
    @service_fallback("jarvis_semantic_router_service")
    def jarvis_winning_patterns():
        """Expose UserKnowledge winning patterns for UI / debugging."""
        svc = getattr(ctx, "jarvis_semantic_router_service", None)
        payload = svc.match_winning_patterns(_uid())
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/command/plan")
    @login_required
    def command_plan():
        """Parse a compound Jarvis command into confirmable triggers/actions."""
        from ...modules.ai_agent.services.command_plan_service import CommandPlanService
        body = request.get_json(silent=True) or {}
        command = (body.get("command") or body.get("query") or "").strip()
        if not command:
            raise ValidationError("command_required")
        plan_svc = CommandPlanService()
        if body.get("semantic", True):
            payload = plan_svc.build_semantic_plan(
                command,
                user_id=_uid(),
                knowledge=getattr(ctx, "user_knowledge_service", None),
            )
        else:
            payload = plan_svc.build_plan(command)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    blueprint.register_blueprint(Blueprint("_jarvis_dummy", __name__))
