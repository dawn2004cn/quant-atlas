from __future__ import annotations

"""Optimization phase API (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.optimization import (
    register_optimization_budget_routes,
    register_optimization_compliance_routes,
    register_optimization_dual_path_routes,
    register_optimization_evolution_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(
    name="optimization",
    context="system",
    description="Optimization: Dual-Path, Compliance, Budget, Evolution",
)
def register_optimization_routes(bp: Blueprint, ctx: ApiV1Context) -> None:
    optimization_bp = Blueprint("optimization", __name__, url_prefix="/optimization")
    register_optimization_dual_path_routes(optimization_bp, ctx)
    register_optimization_compliance_routes(optimization_bp, ctx)
    register_optimization_budget_routes(optimization_bp, ctx)
    register_optimization_evolution_routes(optimization_bp, ctx)
    bp.register_blueprint(optimization_bp)
