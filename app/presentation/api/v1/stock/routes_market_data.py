from __future__ import annotations

"""Stock market data routes (longhu-band, research-reports)."""

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.core.registry import register_routes
from app.domain.enums import MarketCode

from ...common import ok_response, parse_market
from ...decorators import service_fallback
from ...request_parsers import parse_int_param


@register_routes(name="stock_market_data", context="market_data", description="Stock market data endpoints")
def register_stock_market_data(blueprint: Blueprint, ctx) -> None:


    legacy = ctx.enable_legacy_response_fields
    basic_market_data_service = ctx.basic_market_data_service
    fundamental_access = ctx.fundamental_access
    @blueprint.get("/stocks/<market>/<symbol>/longhu-band")
    @login_required
    @service_fallback("basic_market_data_service")
    def stock_longhu_band(market: str, symbol: str):






        m = parse_market(market)






        if m != MarketCode.CN:






            raise ValidationError("longhu-band supports CN only")






        lim = parse_int_param(request.args.get("limit"), name="limit", default=25, min_value=1)






        lim = min(lim, 100)






        items = basic_market_data_service.longhu_for_stock(symbol, limit=lim)






        latest = basic_market_data_service.repository.latest_longhu_trade_date()






        top_d = str(items[0].get("trade_date") or "")[:10] if items else ""






        on_latest_snapshot = bool(latest and top_d == latest)






        return ok_response(






            data={






                "items": items,






                "latest_market_date": latest,






                "on_latest_longhu": on_latest_snapshot,






            },






            legacy_alias_key=None,






            enable_legacy_alias=legacy,






        )


    @blueprint.get("/stocks/<market>/<symbol>/research-reports")
    @login_required
    @service_fallback("fundamental_access")
    def stock_research_reports(market: str, symbol: str):






        m = parse_market(market)






        if m != MarketCode.CN:






            raise ValidationError("research-reports endpoint supports CN market only")






        limit = parse_int_param(request.args.get("limit"), name="limit", default=30, min_value=1)






        limit = min(limit, 100)






        rows, err = fundamental_access.cn_research_reports(symbol, limit=limit)






        payload = {"reports": rows, "limit": limit, "error": err}






        return ok_response(






            data=payload,






            legacy_alias_key=None,






            enable_legacy_alias=legacy,






            count=len(rows),








        )
