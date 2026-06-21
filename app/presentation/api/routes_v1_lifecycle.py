from __future__ import annotations

"""Lifecycle optimization API (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.lifecycle import (
    register_lifecycle_data_routes,
    register_lifecycle_execution_routes,
    register_lifecycle_monitoring_routes,
    register_lifecycle_research_routes,
    register_lifecycle_simulation_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(
    name="lifecycle",
    context="system",
    description="Lifecycle: Data, Research, Simulation, Execution, Monitoring",
)
def register_lifecycle_routes(bp: Blueprint, ctx: ApiV1Context) -> None:
    lifecycle_bp = Blueprint("lifecycle", __name__, url_prefix="/lifecycle")
    register_lifecycle_data_routes(lifecycle_bp, ctx)
    register_lifecycle_research_routes(lifecycle_bp, ctx)
    register_lifecycle_simulation_routes(lifecycle_bp, ctx)
    register_lifecycle_execution_routes(lifecycle_bp, ctx)
    register_lifecycle_monitoring_routes(lifecycle_bp, ctx)
    bp.register_blueprint(lifecycle_bp)
