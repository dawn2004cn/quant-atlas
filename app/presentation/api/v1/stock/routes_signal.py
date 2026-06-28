from __future__ import annotations

"""Stock attribution timeline route."""

from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes
from ...common import ok_response, parse_market
from ...request_parsers import parse_int_param


@register_routes(name="stock_signal", context="market_data", description="Stock attribution timeline")
def register_stock_signal(blueprint: Blueprint, ctx) -> None:

    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/stocks/<market>/<symbol>/attribution-timeline")
    @login_required
    def stock_attribution_timeline(market: str, symbol: str):

        from app.modules.system.services.ui.attribution_timeline_service import (
            AttributionTimelineService,
        )

        limit = parse_int_param(
            request.args.get("limit"),
            name="limit",
            default=80,
            min_value=1,
            max_value=200,
        )

        service = AttributionTimelineService(
            stock_service=ctx.stock_service,
            news_archive=ctx.news_archive,
            fundamental_access=ctx.fundamental_access,
            basic_market_data_service=ctx.basic_market_data_service,
        )

        payload = service.build_timeline(
            symbol,
            parse_market(market),
            start=request.args.get("start"),
            end=request.args.get("end"),
            limit=limit,
        )

        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            count=len(payload["markers"]),
        )
