from __future__ import annotations

"""API v1: Portfolio management routes (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.route_deps import PortfolioRouteDeps, build_portfolio_route_deps
from app.presentation.api.v1.portfolio import (
    register_portfolio_core_routes,
    register_portfolio_detail_routes,
    register_portfolio_trade_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="portfolio", context="portfolio_risk", description="Portfolio management routes")
def register_portfolio_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    deps: PortfolioRouteDeps | None = None,
) -> None:
    route_deps = deps or build_portfolio_route_deps(ctx)
    register_portfolio_core_routes(blueprint, ctx, route_deps=route_deps)
    register_portfolio_detail_routes(blueprint, ctx, route_deps=route_deps)
    register_portfolio_trade_routes(blueprint, ctx, route_deps=route_deps)
