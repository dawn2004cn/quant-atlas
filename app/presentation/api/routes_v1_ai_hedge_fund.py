from __future__ import annotations

"""API routes for AI Hedge Fund integration (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.ai_hedge_fund import (
    AiHedgeFundRuntime,
    register_ai_hedge_fund_analyze_routes,
    register_ai_hedge_fund_query_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="ai_hedge_fund", context="ai_agent", description="AI Hedge Fund integration")
def register_ai_hedge_fund_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    ai_hedge_fund_bp = Blueprint("ai_hedge_fund", __name__, url_prefix="/ai-hedge-fund")
    runtime = AiHedgeFundRuntime(ctx=ctx)
    register_ai_hedge_fund_analyze_routes(ai_hedge_fund_bp, ctx, runtime=runtime)
    register_ai_hedge_fund_query_routes(ai_hedge_fund_bp, ctx, runtime=runtime)
    blueprint.register_blueprint(ai_hedge_fund_bp)
