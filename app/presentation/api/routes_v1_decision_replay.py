from __future__ import annotations

"""Decision Replay Space API — 2.5D immersive behavior + evidence scene."""

from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from .common import ok_response
from .decorators import service_fallback
from .request_parsers import parse_int_param
from .v1_context import ApiV1Context


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="decision_replay", context="research", description="Decision Replay Space API (2.5D immersive)")
def register_decision_replay_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/decision-replay/space")
    @login_required
    @service_fallback("decision_replay_space_service")
    def decision_replay_space():
        """Build 3D scene from behavior topology + optional symbol timeline."""
        symbol = (request.args.get("symbol") or "").strip() or None
        market = (request.args.get("market") or "CN").strip().upper()
        minutes_back = parse_int_param(
            request.args.get("minutes_back"),
            name="minutes_back",
            default=120,
            min_value=5,
        )
        minutes_back = min(minutes_back, 720)
        svc = getattr(ctx, "decision_replay_space_service", None)
        payload = svc.build_space(
            _uid(),
            symbol=symbol,
            market=market,
            minutes_back=minutes_back,
        )
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "scene_build_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
