from __future__ import annotations

"""API v1: Data source optimization routes (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.route_deps import DataOptimizerRouteDeps, build_data_optimizer_route_deps
from app.presentation.api.v1.data_optimizer import (
    register_data_optimizer_scenario_routes,
    register_data_optimizer_tdx_routes,
    register_data_optimizer_write_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="data_optimizer", context="data", description="Data source optimization routes")
def register_data_optimizer_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    deps: DataOptimizerRouteDeps | None = None,
) -> None:
    _ = deps or build_data_optimizer_route_deps(ctx)
    register_data_optimizer_scenario_routes(blueprint, ctx)
    register_data_optimizer_tdx_routes(blueprint, ctx)
    register_data_optimizer_write_routes(blueprint, ctx)
