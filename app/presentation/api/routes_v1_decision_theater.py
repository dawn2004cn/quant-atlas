from __future__ import annotations

"""Decision Theater API — immersive research pipeline scene (Quant Atlas 9.0 Step Five)."""

from flask import Blueprint
from flask_login import current_user, login_required

from app.core.registry import register_routes

from .common import ok_response
from .decorators import service_fallback
from .v1_context import ApiV1Context


@register_routes(name="decision_theater", context="research", description="Decision Theater API (Quant Atlas 9.0 Step Five)")
def register_decision_theater_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/decision-theater/space")
    @login_required
    @service_fallback("decision_theater_service")
    def decision_theater_space():
        svc = getattr(ctx, "decision_theater_service", None)
        payload = svc.build_theater(getattr(current_user, "id", None))
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
