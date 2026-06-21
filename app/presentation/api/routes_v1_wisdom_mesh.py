"""Wisdom Mesh API routes (dispatcher)."""

from __future__ import annotations

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.wisdom_mesh import (
    WisdomMeshRuntime,
    register_wisdom_mesh_leaderboard_routes,
    register_wisdom_mesh_strategy_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(
    name="wisdom_mesh",
    context="strategy",
    description="Wisdom Mesh — democratic strategy sharing and crowdfactor experiments",
)
def register_wisdom_mesh_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = WisdomMeshRuntime(ctx=ctx)
    wisdom_mesh_bp = Blueprint("wisdom_mesh", __name__, url_prefix="/wisdom-mesh")
    register_wisdom_mesh_strategy_routes(wisdom_mesh_bp, ctx, runtime=runtime)
    register_wisdom_mesh_leaderboard_routes(wisdom_mesh_bp, ctx, runtime=runtime)
    blueprint.register_blueprint(wisdom_mesh_bp)
