"""Strategy Synthesis API routes (dispatcher)."""

from __future__ import annotations

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.strategy_synthesis import (
    StrategySynthesisRuntime,
    register_strategy_synthesis_evidence_routes,
    register_strategy_synthesis_pipeline_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(
    name="strategy_synthesis",
    context="strategy",
    description="Natural language to StrategySpec AST pipeline",
)
def register_strategy_synthesis_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = StrategySynthesisRuntime(ctx=ctx)
    strategy_synthesis_bp = Blueprint(
        "strategy_synthesis",
        __name__,
        url_prefix="/strategy/synthesis",
    )
    register_strategy_synthesis_pipeline_routes(strategy_synthesis_bp, ctx, runtime=runtime)
    register_strategy_synthesis_evidence_routes(strategy_synthesis_bp, ctx, runtime=runtime)
    blueprint.register_blueprint(strategy_synthesis_bp)
