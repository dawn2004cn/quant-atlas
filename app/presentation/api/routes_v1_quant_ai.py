from __future__ import annotations

"""API v1: quant/AI endpoints (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.route_deps import AiRouteDeps, build_ai_route_deps
from app.presentation.api.v1.quant_ai import (
    QuantAiRuntime,
    register_quant_ai_analysis_routes,
    register_quant_ai_llm_routes,
    register_quant_ai_prediction_routes,
    register_quant_ai_selection_routes,
    register_quant_ai_strategy_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="quant_ai", context="ai_agent", description="Quant/AI strategy and analysis endpoints")
def register_quant_ai_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
    *,
    deps: AiRouteDeps | None = None,
) -> None:
    blueprint.name = "quant_ai"
    route_deps = deps or build_ai_route_deps(ctx)
    runtime = QuantAiRuntime.from_deps(route_deps)
    register_quant_ai_strategy_routes(blueprint, ctx, runtime=runtime)
    register_quant_ai_prediction_routes(blueprint, ctx, runtime=runtime)
    register_quant_ai_selection_routes(blueprint, ctx, runtime=runtime)
    register_quant_ai_analysis_routes(blueprint, ctx, runtime=runtime)
    register_quant_ai_llm_routes(blueprint, ctx, runtime=runtime)
