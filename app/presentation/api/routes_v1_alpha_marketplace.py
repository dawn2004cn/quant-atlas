"""API v1: Alpha Marketplace dispatcher."""

from __future__ import annotations

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.alpha_marketplace import (
    register_alpha_marketplace_reputation_routes,
    register_alpha_marketplace_trade_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="alpha_marketplace", context="system", description="Alpha factor marketplace — contribute/reward via reputation")
def register_alpha_marketplace_routes(bp: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields
    register_alpha_marketplace_trade_routes(bp, ctx, legacy=legacy)
    register_alpha_marketplace_reputation_routes(bp, ctx, legacy=legacy)
