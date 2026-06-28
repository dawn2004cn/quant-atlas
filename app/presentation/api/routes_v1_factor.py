from __future__ import annotations

"""API v1: Factor routes (dispatcher)."""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.factor import (
    register_factor_calculate_routes,
    register_factor_ortho_routes,
    register_factor_self_correction_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="factor", context="strategy", description="Factor orthogonalization and self-correction routes")
def register_factor_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    register_factor_ortho_routes(blueprint, ctx)
    register_factor_self_correction_routes(blueprint, ctx)
    register_factor_calculate_routes(blueprint, ctx)
