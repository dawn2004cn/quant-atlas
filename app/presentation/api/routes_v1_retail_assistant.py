from __future__ import annotations

"""Retail assistant hub API routes (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.retail_assistant import (
    RetailAssistantRuntime,
    register_retail_assistant_hub_routes,
    register_retail_assistant_insight_routes,
    register_retail_assistant_psychology_routes,
    register_retail_assistant_shadow_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes
def register_retail_assistant_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = RetailAssistantRuntime(ctx=ctx)
    register_retail_assistant_hub_routes(blueprint, ctx, runtime=runtime)
    register_retail_assistant_insight_routes(blueprint, ctx, runtime=runtime)
    register_retail_assistant_psychology_routes(blueprint, ctx, runtime=runtime)
    register_retail_assistant_shadow_routes(blueprint, ctx, runtime=runtime)
