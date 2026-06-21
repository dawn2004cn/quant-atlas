"""Longhu and yanbao feed routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.modules.system.services.ui.data_freshness_service import enrich_market_payload
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.market_aux.runtime import MarketAuxRuntime
from app.presentation.api.v1_context import ApiV1Context
from ...decorators import service_fallback


def register_market_aux_feed_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: MarketAuxRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/market/longhu")
    @login_required
    @service_fallback("basic_market_data_service")
    def market_longhu_list():
        """龙虎榜列表（本地库 ``instance/basic_market_data.db``）；``date`` 可选 YYYY-MM-DD。"""
        basic_market_data_service = getattr(ctx, "basic_market_data_service", None)
        date_arg = (request.args.get("date") or "").strip() or None
        lim = parse_int_param(request.args.get("limit"), name="limit", default=400, min_value=1)
        lim = min(lim, 800)
        td, items = basic_market_data_service.longhu_day(date_arg, limit=lim)
        dates = basic_market_data_service.repository.list_longhu_latest_dates(limit=20)
        latest_upd = ""
        for row in items:
            stamp = str((row or {}).get("updated_at") or "")
            if stamp > latest_upd:
                latest_upd = stamp
        payload = enrich_market_payload(
            {
                "trade_date": td or "",
                "snapshot_at": td or "",
                "updated_at": latest_upd or td or "",
            },
            source="longhu_bang",
        )
        payload["trade_date"] = td
        payload["items"] = items
        payload["available_dates"] = dates
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            count=len(items),
        )

    @blueprint.get("/market/yanbao")
    @login_required
    @service_fallback("basic_market_data_service")
    def market_yanbao_feed():
        """研报聚合（定时抓取入库）；``category`` 可选。"""
        basic_market_data_service = getattr(ctx, "basic_market_data_service", None)
        cat = (request.args.get("category") or "").strip() or None
        lim = parse_int_param(request.args.get("limit"), name="limit", default=60, min_value=1)
        lim = min(lim, 200)
        items = basic_market_data_service.yanbao_list(category=cat, limit=lim)
        latest_pub = ""
        for row in items:
            stamp = str((row or {}).get("pub_date") or "")
            if stamp > latest_pub:
                latest_pub = stamp
        payload = enrich_market_payload(
            {"updated_at": latest_pub, "snapshot_at": latest_pub},
            source="yanbao_hub",
        )
        payload["items"] = items
        payload["category"] = cat
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            count=len(items),
        )
