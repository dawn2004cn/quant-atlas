from __future__ import annotations

"""Stock news routes."""

from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes
from ...common import ok_response, parse_market
from ...decorators import service_fallback
from ...request_parsers import parse_int_param


@register_routes(name="stock_news", context="market_data", description="Stock news endpoints")
def register_stock_news(blueprint: Blueprint, ctx) -> None:


    legacy = ctx.enable_legacy_response_fields
    stock_service = ctx.stock_service
    news_archive = ctx.news_archive
    @blueprint.get("/stocks/<market>/<symbol>/news")
    @login_required
    @service_fallback("stock_service")
    def stock_news(market: str, symbol: str):






        snapshot = stock_service.get_news_snapshot(symbol, parse_market(market))






        if isinstance(snapshot, list):






            news_data = [item.model_dump() if hasattr(item, "model_dump") else item for item in snapshot]






            data = {"news": news_data, "industry_news": []}






        else:






            snapshot_dict = snapshot.model_dump() if hasattr(snapshot, "model_dump") else snapshot






            data = {"news": snapshot_dict.get("news", []), "industry_news": snapshot_dict.get("industry_news", [])}






        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)


    @blueprint.get("/stocks/<market>/<symbol>/news-archive")
    @login_required
    @service_fallback("news_archive")
    def stock_news_archive(market: str, symbol: str):






        m = parse_market(market)






        limit = parse_int_param(request.args.get("limit"), name="limit", default=80, min_value=1)






        limit = min(limit, 200)






        items = news_archive.list_for_symbol(m.value, symbol, limit=limit)






        meta = news_archive.get_meta(m.value, symbol)






        return ok_response(






            data={"items": items, "meta": meta},






            legacy_alias_key=None,






            enable_legacy_alias=legacy,






            market=m.value,






            symbol=symbol,






            count=len(items),






        )
