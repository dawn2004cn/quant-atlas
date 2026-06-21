from __future__ import annotations

"""API v1：Qlib 管线、研究闭环快照、RD-Agent、Alpha Factory（dispatcher）。"""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.qlib_rd import (
    register_alpha_factory_routes,
    register_qlib_pipeline_routes,
    register_rd_agent_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="qlib_rd", context="data", description="Qlib pipeline, RD-Agent, Alpha Factory")
def register_qlib_rd_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register qlib / rd-agent / alpha-factory routes via sub-modules."""
    register_qlib_pipeline_routes(blueprint, ctx)
    register_rd_agent_routes(blueprint, ctx)
    register_alpha_factory_routes(blueprint, ctx)
