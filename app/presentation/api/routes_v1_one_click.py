"""One-Click API routes (dispatcher)."""

from __future__ import annotations

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.one_click import (
    OneClickRuntime,
    register_one_click_action_routes,
    register_one_click_evidence_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(
    name="one_click",
    context="strategy",
    description="One-Click Station — deploy shared strategies with intent",
)
def register_one_click_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = OneClickRuntime(ctx=ctx)
    one_click_bp = Blueprint("one_click", __name__, url_prefix="/one-click")
    register_one_click_action_routes(one_click_bp, ctx, runtime=runtime)
    register_one_click_evidence_routes(one_click_bp, ctx, runtime=runtime)
    blueprint.register_blueprint(one_click_bp)
