"""Strategy Shadow API — Quant Twin coaching and behavioral analysis (9.0)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from .common import ok_response
from .v1_context import ApiV1Context


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="strategy_shadow", context="strategy", description="Strategy Shadow API (Quant Twin)")
def register_strategy_shadow_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/shadow/profile")
    @login_required
    def shadow_profile():
        """Get user's behavioral shadow profile."""
        svc = getattr(ctx, "strategy_shadow_service", None)
        if svc is None:
            raise ValidationError("strategy_shadow_service_unavailable")
        profile = svc.get_shadow_profile(_uid())
        return ok_response(
            data={"ok": True, "profile": profile},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/shadow/record")
    @login_required
    def shadow_record_decision():
        """Record a user decision for shadow learning."""
        svc = getattr(ctx, "strategy_shadow_service", None)
        if svc is None:
            raise ValidationError("strategy_shadow_service_unavailable")
        body = request.get_json(silent=True) or {}
        action = body.get("action")
        if not action:
            raise ValidationError("action_required")

        profile = svc.record_decision(
            _uid(),
            action=action,
            symbol=body.get("symbol"),
            side=body.get("side"),
            quantity=body.get("quantity"),
            price=body.get("price"),
            context=body.get("context"),
        )
        return ok_response(
            data={"ok": True, "profile": profile},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/shadow/detect")
    @login_required
    def shadow_detect_deviation():
        """Detect if a proposed action deviates from user's normal patterns."""
        svc = getattr(ctx, "strategy_shadow_service", None)
        if svc is None:
            raise ValidationError("strategy_shadow_service_unavailable")
        body = request.get_json(silent=True) or {}
        action = body.get("action")
        if not action:
            raise ValidationError("action_required")

        result = svc.detect_deviation(
            _uid(),
            action=action,
            symbol=body.get("symbol"),
            context=body.get("context"),
        )
        return ok_response(
            data=result,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/shadow/coaching/outcome")
    @login_required
    def shadow_coaching_outcome():
        """Record coaching nudge outcome (accepted/rejected/ignored)."""
        svc = getattr(ctx, "strategy_shadow_service", None)
        if svc is None:
            raise ValidationError("strategy_shadow_service_unavailable")
        body = request.get_json(silent=True) or {}
        nudge_type = body.get("nudge_type")
        outcome = body.get("outcome")
        if not nudge_type or not outcome:
            raise ValidationError("nudge_type_and_outcome_required")

        effectiveness = svc.record_coaching_outcome(
            _uid(),
            nudge_type=nudge_type,
            outcome=outcome,
        )
        return ok_response(
            data={"ok": True, "effectiveness": effectiveness},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/shadow/coaching/stats")
    @login_required
    def shadow_coaching_stats():
        """Get coaching effectiveness statistics."""
        svc = getattr(ctx, "strategy_shadow_service", None)
        if svc is None:
            raise ValidationError("strategy_shadow_service_unavailable")
        stats = svc.get_coaching_stats(_uid())
        return ok_response(
            data={"ok": True, **stats},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
