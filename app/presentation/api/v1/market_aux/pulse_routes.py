"""Market pulse narrative route."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.common import ok_response
from app.presentation.api.v1.market_aux.runtime import MarketAuxRuntime
from app.presentation.api.v1_context import ApiV1Context
from ...decorators import service_fallback


def register_market_aux_pulse_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: MarketAuxRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/markets/pulse")
    @login_required
    @service_fallback("market_narrative_service")
    def market_pulse():
        svc = getattr(ctx, "market_narrative_service", None)
        market = request.args.get("market", "CN").strip().upper()
        data = svc.get_latest_pulse(market)
        return ok_response(legacy_alias_key=None, enable_legacy_alias=legacy, data=data)
