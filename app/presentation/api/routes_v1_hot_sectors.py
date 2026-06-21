from __future__ import annotations

"""API v1：热点板块（dispatcher）。"""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.route_deps import HotSectorRouteDeps, build_hot_sector_route_deps
from app.presentation.api.v1.hot_sectors import (
    HotSectorRuntime,
    register_hot_sector_ingest_routes,
    register_hot_sector_list_routes,
    register_hot_sector_member_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="hot_sector", context="market_data", description="热点板块（涨幅榜 + 成分股 + MySQL 快照）")
def register_hot_sector_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    deps: HotSectorRouteDeps | None = None,
) -> None:
    route_deps = deps or build_hot_sector_route_deps(ctx)
    runtime = HotSectorRuntime.from_deps(route_deps)
    register_hot_sector_list_routes(blueprint, ctx, runtime=runtime)
    register_hot_sector_ingest_routes(blueprint, ctx, runtime=runtime)
    register_hot_sector_member_routes(blueprint, ctx, runtime=runtime)
