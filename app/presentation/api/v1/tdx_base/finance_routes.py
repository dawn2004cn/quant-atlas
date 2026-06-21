"""TDX finance snapshot routes."""

from __future__ import annotations

from flask import Blueprint
from flask_login import login_required

from app.presentation.api.common import ok_response
from app.presentation.api.v1.tdx_base.runtime import TdxBaseRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_tdx_base_finance_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TdxBaseRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    tdx_read = runtime.tdx_read

    @blueprint.get("/tdx/finance/<path:symbol>/latest")
    @login_required
    def tdx_finance_latest(symbol: str):
        """最新一期财务快照（TDX 在线抓取落库结果）。"""
        row = tdx_read.get_latest_finance_snapshot(symbol)
        return ok_response(data=row, legacy_alias_key=None, enable_legacy_alias=legacy)
