from __future__ import annotations

"""API v1：通达信基础数据（板块/股票基础信息）dispatcher。"""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.route_deps import TdxBaseRouteDeps, build_tdx_base_route_deps
from app.presentation.api.v1.tdx_base import (
    TdxBaseRuntime,
    register_tdx_base_block_routes,
    register_tdx_base_finance_routes,
    register_tdx_base_ingest_routes,
    register_tdx_base_watchlist_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="tdx_base", context="market_data", description="通达信板块与基础数据")
def register_tdx_base_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    deps: TdxBaseRouteDeps | None = None,
) -> None:
    route_deps = deps or build_tdx_base_route_deps(ctx)
    runtime = TdxBaseRuntime.from_deps(route_deps)
    register_tdx_base_ingest_routes(blueprint, ctx, runtime=runtime)
    register_tdx_base_block_routes(blueprint, ctx, runtime=runtime)
    register_tdx_base_watchlist_routes(blueprint, ctx, runtime=runtime)
    register_tdx_base_finance_routes(blueprint, ctx, runtime=runtime)
