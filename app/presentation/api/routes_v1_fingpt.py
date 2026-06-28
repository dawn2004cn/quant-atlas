from __future__ import annotations

"""API v1：FinGPT 只读状态与轻量样本。"""


from flask import Blueprint, request
from flask_login import login_required

from ...core.registry import register_routes
from .common import ok_response, require_data_ingestion_role
from .request_parsers import parse_int_param
from .route_deps import FinGptRouteDeps, build_fingpt_route_deps
from .v1_context import ApiV1Context


@register_routes(name="fingpt", context="ai_agent", description="FinGPT 只读状态与轻量样本")
def register_fingpt_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    deps: FinGptRouteDeps | None = None,
) -> None:
    route_deps = deps or build_fingpt_route_deps(ctx)
    legacy = route_deps.enable_legacy_response_fields
    fingpt = route_deps.fingpt_application_service

    @blueprint.get("/fingpt/status")
    @login_required
    def fingpt_status():
        """FinGPT MySQL 读写策略 + 行数 + 最近 tickers（不触发外部推理）。"""
        data = fingpt.probe_integration_stack_layer()
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/fingpt/recent")
    @login_required
    def fingpt_recent():
        """返回最近预测/情感的 ticker 列表（仅用于 UI 轻展示）。"""
        lim = parse_int_param(request.args.get("limit"), name="limit", default=5, min_value=1)
        lim = min(int(lim), 50)
        data = fingpt.recent_tickers(limit=lim)
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/fingpt/predictions")
    @login_required
    def fingpt_recent_predictions():
        """只读：最近预测列表（可按 ticker 过滤）。"""
        lim = parse_int_param(request.args.get("limit"), name="limit", default=20, min_value=1)
        lim = min(int(lim), 200)
        ticker = (request.args.get("ticker") or "").strip() or None
        source = (request.args.get("source") or "").strip() or None
        since_hours = parse_int_param(request.args.get("since_hours"), name="since_hours", default=0, min_value=0)
        data = fingpt.list_recent_predictions(limit=lim, ticker=ticker, source=source, since_hours=since_hours)
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/fingpt/sentiments")
    @login_required
    def fingpt_recent_sentiments():
        """只读：最近情感列表（可按 ticker 过滤）。"""
        lim = parse_int_param(request.args.get("limit"), name="limit", default=20, min_value=1)
        lim = min(int(lim), 200)
        ticker = (request.args.get("ticker") or "").strip() or None
        source = (request.args.get("source") or "").strip() or None
        since_hours = parse_int_param(request.args.get("since_hours"), name="since_hours", default=0, min_value=0)
        data = fingpt.list_recent_sentiments(limit=lim, ticker=ticker, source=source, since_hours=since_hours)
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/fingpt/dupes")
    @login_required
    def fingpt_dupes_preview():
        """只读：重复组预览（不删除）——判断是否需要执行去重脚本。"""
        ticker = (request.args.get("ticker") or "").strip() or None
        sample = parse_int_param(request.args.get("sample"), name="sample", default=20, min_value=0)
        sample = min(int(sample), 200)
        data = fingpt.dupes_preview(ticker=ticker, sample=sample)
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/fingpt/dedupe/apply")
    @login_required
    def fingpt_dedupe_apply():
        """写：执行去重（保留最新 id）；需要数据入库权限。"""
        require_data_ingestion_role()
        payload = request.get_json(silent=True) or {}
        ticker = (payload.get("ticker") or "").strip() or None
        data = fingpt.dedupe_apply(ticker=ticker)
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)
