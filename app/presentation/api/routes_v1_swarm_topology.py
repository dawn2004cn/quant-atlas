from __future__ import annotations

"""Swarm Designer API — topology presets and user-defined graphs (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.swarm_topology import (
    SwarmTopologyRuntime,
    register_swarm_topology_adaptive_routes,
    register_swarm_topology_core_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="swarm_topology", context="research", description="Swarm Designer API (topology presets)")
def register_swarm_topology_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = SwarmTopologyRuntime(ctx=ctx)
    register_swarm_topology_core_routes(blueprint, ctx, runtime=runtime)
    register_swarm_topology_adaptive_routes(blueprint, ctx, runtime=runtime)
