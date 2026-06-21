from __future__ import annotations

"""API v1：自选股、分组、用户与密码路由（dispatcher）。"""

import logging

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.route_deps import PortfolioUserRouteDeps, build_portfolio_user_route_deps
from app.presentation.api.v1.portfolio_users import (
    PortfolioUserRuntime,
    register_portfolio_stock_group_routes,
    register_portfolio_user_admin_routes,
    register_portfolio_watchlist_routes,
)
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


@register_routes(name="portfolio_user", context="portfolio", description="自选股、分组与用户密码")
def register_portfolio_user_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
    *,
    deps: PortfolioUserRouteDeps | None = None,
) -> None:
    route_deps = deps or build_portfolio_user_route_deps(ctx)
    runtime = PortfolioUserRuntime(ctx=ctx, deps=route_deps)

    # Warn only when deps are truly missing (runtime fallback needs request context)
    if route_deps.watchlist_service is None:
        logger.warning("watchlist_service unavailable — watchlist routes will return 503")
    if route_deps.stock_group_service is None:
        logger.warning("stock_group_service unavailable — portfolio group routes will return 503")

    register_portfolio_watchlist_routes(blueprint, ctx, runtime=runtime)
    register_portfolio_stock_group_routes(blueprint, ctx, runtime=runtime)
    register_portfolio_user_admin_routes(blueprint, ctx, runtime=runtime)
