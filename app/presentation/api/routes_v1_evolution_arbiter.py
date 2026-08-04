"""Phase 8.1 Evolution Arbiter route — extends panorama with evolve/status."""
from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.presentation.api.common import ok_response
from app.presentation.api.decorators import service_fallback
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


@register_routes(name="evolution_arbiter", context="system", description="Autonomous strategy evolution")
def register_evolution_arbiter_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/panorama/evolution/status")
    @login_required
    @service_fallback("evolution_arbiter_service")
    def evolution_status():
        svc = getattr(ctx, "evolution_arbiter_service", None)
        return ok_response(data=svc.get_status(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/panorama/evolution/evolve")
    @login_required
    @service_fallback("evolution_arbiter_service")
    def evolution_evolve():
        svc = getattr(ctx, "evolution_arbiter_service", None)
        payload = request.get_json(silent=True) or {}
        symbol = str(payload.get("symbol", "000001")).strip().upper()
        market = str(payload.get("market", "CN")).strip().upper() or "CN"
        return ok_response(
            data=svc.evolve(symbol=symbol, market=market, context=payload),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
