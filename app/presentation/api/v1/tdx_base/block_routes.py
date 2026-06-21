"""TDX block list, summary and member routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.modules.data.services.tdx_block_stats_service import TdxBlockStatsService
from app.presentation.api.common import ok_collection, ok_response
from app.presentation.api.request_parsers import parse_int_param, parse_optional_bool_param
from app.presentation.api.v1.tdx_base.runtime import TdxBaseRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_tdx_base_block_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TdxBaseRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    tdx_read = runtime.tdx_read

    @blueprint.get("/tdx/blocks")
    @login_required
    def tdx_blocks():
        """列出板块（按 kind）。"""
        kind = (request.args.get("kind") or "").strip().lower()
        if kind and kind not in ("zs", "gn", "fg"):
            raise ValidationError("kind must be zs/gn/fg")
        rows = tdx_read.list_blocks(block_kind=kind or None)
        return ok_collection(items=rows, item_key="items", enable_legacy_alias=legacy)

    @blueprint.get("/tdx/blocks/summaries")
    @login_required
    def tdx_block_summaries():
        """通达信板块汇总：涨幅、涨股比、龙头（基于成分股行情）。"""
        kind = (request.args.get("kind") or "").strip().lower()
        limit = parse_int_param(request.args.get("limit"), name="limit", default=60, min_value=1, max_value=120)
        items = TdxBlockStatsService().list_block_summaries(block_kind=kind, limit=limit)
        return ok_collection(items=items, item_key="items", enable_legacy_alias=legacy)

    @blueprint.get("/tdx/blocks/<block_kind>/<path:block_name>/summary")
    @login_required
    def tdx_block_summary(block_kind: str, block_name: str):
        """单板块汇总指标。"""
        kind = (block_kind or "").strip().lower()
        if kind not in ("zs", "gn", "fg"):
            raise ValidationError("block_kind must be zs/gn/fg")
        name = (block_name or "").strip()
        if not name:
            raise ValidationError("block_name is required")
        stats = TdxBlockStatsService().block_summary(kind, name)
        return ok_response(
            data={"block_kind": kind, "block_name": name, **(stats or {})},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/tdx/blocks/<block_kind>/<path:block_name>/members")
    @login_required
    def tdx_block_members(block_kind: str, block_name: str):
        """板块成分股列表（含名称）；``with_quotes=1`` 时服务端批量附带行情。"""
        kind = (block_kind or "").strip().lower()
        if kind not in ("zs", "gn", "fg"):
            raise ValidationError("block_kind must be zs/gn/fg")
        name = (block_name or "").strip()
        if not name:
            raise ValidationError("block_name is required")
        with_quotes = parse_optional_bool_param(request.args.get("with_quotes"), name="with_quotes")
        member_limit = parse_int_param(
            request.args.get("limit"), name="limit", default=300, min_value=1, max_value=500
        )
        if with_quotes:
            rows = TdxBlockStatsService().list_members_with_quotes(kind, name, limit=member_limit)
            return ok_collection(items=rows, item_key="items", enable_legacy_alias=legacy)

        rows = tdx_read.list_block_members(block_kind=kind, block_name=name, limit=member_limit)
        return ok_collection(items=rows, item_key="items", enable_legacy_alias=legacy)

    @blueprint.get("/tdx/symbols/<path:symbol>/blocks")
    @login_required
    def tdx_symbol_blocks(symbol: str):
        """反向查询：个股所属通达信板块（来自 MySQL ``tdx_block_items``）。"""
        rows = tdx_read.list_symbol_blocks(symbol)
        return ok_collection(items=rows, item_key="items", enable_legacy_alias=legacy)
