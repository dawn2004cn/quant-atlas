from __future__ import annotations

"""Federated Agent Mesh API dispatcher."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.mesh import (
    MeshRuntime,
    register_mesh_gateway_routes,
    register_mesh_perception_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="mesh", context="mesh", description="Federated Agent Mesh API (9.0)")
def register_mesh_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = MeshRuntime(ctx=ctx)
    register_mesh_gateway_routes(blueprint, ctx, runtime=runtime)
    register_mesh_perception_routes(blueprint, ctx, runtime=runtime)
