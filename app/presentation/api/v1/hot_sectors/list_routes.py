"""Hot sector list and snapshot routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.common import ok_collection
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.hot_sectors.runtime import HotSectorRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_hot_sector_list_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: HotSectorRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    storage = runtime.storage

    @blueprint.get("/hot-sectors")
    @login_required
    def list_hot_sectors():
        """热点板块 Top N；``source=auto|live|mysql``，``snapshot_at`` 指定历史快照。"""
        return runtime.sectors_response()

    @blueprint.get("/data/hot-sectors")
    @login_required
    def list_hot_sectors_legacy():
        """兼容旧路径 /api/v1/data/hot-sectors。"""
        return runtime.sectors_response()

    @blueprint.get("/hot-sectors/snapshots")
    @login_required
    def list_hot_sector_snapshots():
        """已入库快照列表（需 MySQL）。"""
        limit = parse_int_param(request.args.get("limit"), name="limit", default=30, min_value=1, max_value=200)
        items = storage.list_snapshots(limit=limit)
        return ok_collection(items=items, item_key="items", enable_legacy_alias=legacy)
