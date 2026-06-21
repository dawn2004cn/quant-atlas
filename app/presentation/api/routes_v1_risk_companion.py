"""Risk Companion API routes (dispatcher)."""

from __future__ import annotations

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.risk_companion import (
    RiskCompanionRuntime,
    register_risk_companion_detect_routes,
    register_risk_companion_profile_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(
    name="risk_companion",
    context="risk",
    description="Risk Companion — emotional intelligence layer for retail users",
)
def register_risk_companion_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = RiskCompanionRuntime(ctx=ctx)
    risk_companion_bp = Blueprint("risk_companion", __name__, url_prefix="/risk/companion")
    register_risk_companion_detect_routes(risk_companion_bp, ctx, runtime=runtime)
    register_risk_companion_profile_routes(risk_companion_bp, ctx, runtime=runtime)
    blueprint.register_blueprint(risk_companion_bp)
