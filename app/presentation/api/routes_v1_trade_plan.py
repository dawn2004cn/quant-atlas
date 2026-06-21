from __future__ import annotations

"""API v1：买卖计划与风控卡片（dispatcher）。"""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.trade_plan import (
    TradePlanRuntime,
    register_decision_review_routes,
    register_trade_plan_core_routes,
    register_trade_review_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="trade_plan", context="portfolio_risk", description="买卖计划与风控卡片")
def register_trade_plan_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register trade plan endpoints."""
    runtime = TradePlanRuntime(ctx=ctx)
    register_trade_plan_core_routes(blueprint, ctx, runtime=runtime)
    register_trade_review_routes(blueprint, ctx, runtime=runtime)
    register_decision_review_routes(blueprint, ctx, runtime=runtime)
