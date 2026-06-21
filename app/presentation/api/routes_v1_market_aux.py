from __future__ import annotations

"""Market auxiliary routes dispatcher (longhu, yanbao, pulse)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.market_aux import (
    MarketAuxRuntime,
    register_market_aux_feed_routes,
    register_market_aux_pulse_routes,
    register_market_aux_refresh_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(
    name="market_aux",
    context="market_data",
    description="Market auxiliary routes (longhu, yanbao, pulse)",
)
def register_market_aux_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = MarketAuxRuntime(ctx=ctx)
    register_market_aux_feed_routes(blueprint, ctx, runtime=runtime)
    register_market_aux_pulse_routes(blueprint, ctx, runtime=runtime)
    register_market_aux_refresh_routes(blueprint, ctx, runtime=runtime)
