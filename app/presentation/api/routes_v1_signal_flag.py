from __future__ import annotations

"""API v1：信号旗股票池（dispatcher）。"""

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.signal_flag import (
    SignalFlagRuntime,
    register_signal_flag_backfill_routes,
    register_signal_flag_query_routes,
    register_signal_flag_scan_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes
def register_signal_flag_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    runtime = SignalFlagRuntime(ctx=ctx)
    register_signal_flag_query_routes(blueprint, ctx, runtime=runtime)
    register_signal_flag_scan_routes(blueprint, ctx, runtime=runtime)
    register_signal_flag_backfill_routes(blueprint, ctx, runtime=runtime)
