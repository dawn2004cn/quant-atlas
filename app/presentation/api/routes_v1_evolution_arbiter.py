"""Phase 8.1 Evolution Arbiter route — extends panorama with evolve/status."""
from __future__ import annotations

from flask import Blueprint
from flask_login import login_required

from app.core.registry import register_routes
from app.core.middleware.request_context import require_authenticated_user_id
from app.presentation.api.common import ok_response
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="evolution_arbiter", context="system", description="Autonomous strategy evolution")
def register_evolution_arbiter_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/panorama/evolution/status")
    @login_required
    def evolution_status():
        svc = getattr(ctx, "evolution_arbiter_service", None)
        if svc is None:
            return ok_response(
                data={"error": "evolution_arbiter_unavailable"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        return ok_response(data=svc.get_status(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/panorama/evolution/evolve")
    @login_required
    def evolution_evolve():
        svc = getattr(ctx, "evolution_arbiter_service", None)
        if svc is None:
            return ok_response(
                data={"error": "evolution_arbiter_unavailable"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        payload = {}
        try:
            from flask import request

            payload = request.get_json(silent=True) or {}
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        symbol = str(payload.get("symbol", "000001")).strip().upper()
        market = str(payload.get("market", "CN")).strip().upper() or "CN"
        challenger_count = int(payload.get("challenger_count", 2) or 2)
        result = svc.evolve(symbol=symbol, market=market, challenger_count=challenger_count)
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)
