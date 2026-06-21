"""TDX watchlist routes."""

from __future__ import annotations

from flask import Blueprint
from flask_login import login_required

from app.presentation.api.common import ok_collection
from app.presentation.api.v1.tdx_base.runtime import TdxBaseRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_tdx_base_watchlist_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TdxBaseRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    tdx_read = runtime.tdx_read

    @blueprint.get("/tdx/watchlists")
    @login_required
    def tdx_watchlists():
        """列出本地 ``.blk`` 自选/板块文件导入的 watchlists。"""
        rows = tdx_read.list_watchlists()
        return ok_collection(items=rows, item_key="items", enable_legacy_alias=legacy)

    @blueprint.get("/tdx/watchlists/<path:name>/members")
    @login_required
    def tdx_watchlist_members(name: str):
        """watchlist 成分股（含名称）。"""
        rows = tdx_read.list_watchlist_members(watchlist_name=name)
        return ok_collection(items=rows, item_key="items", enable_legacy_alias=legacy)
