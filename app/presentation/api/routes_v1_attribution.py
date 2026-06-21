"""Attribution API routes (dispatcher)."""

from __future__ import annotations

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.attribution import (
    AttributionRuntime,
    register_attribution_analyze_routes,
    register_attribution_whatif_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="attribution", context="strategy", description="Performance attribution analysis")
def register_attribution_routes(blueprint: Blueprint, ctx: ApiV1Context | None = None) -> None:
    """Register attribution routes to blueprint."""
    attribution_bp = Blueprint("attribution", __name__, url_prefix="/attribution")
    runtime = AttributionRuntime(ctx=ctx)
    register_attribution_analyze_routes(attribution_bp, ctx, runtime=runtime)
    register_attribution_whatif_routes(attribution_bp, ctx, runtime=runtime)
    blueprint.register_blueprint(attribution_bp)
