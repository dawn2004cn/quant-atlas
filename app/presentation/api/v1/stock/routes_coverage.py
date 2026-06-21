from __future__ import annotations

"""Stock data coverage route."""

from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes
from ...common import ok_response, parse_market
from ...decorators import service_fallback
from ...request_parsers import parse_int_param


@register_routes(name="stock_coverage", context="market_data", description="Data coverage")
def register_stock_coverage(blueprint: Blueprint, ctx) -> None:


    legacy = ctx.enable_legacy_response_fields
    stock_service = ctx.stock_service


    @blueprint.get("/stocks/<market>/<symbol>/data-coverage")
    @login_required
    @service_fallback("stock_service")
    def stock_data_coverage(market: str, symbol: str):






        from app.modules.market_data.services.data_coverage_service import DataCoverageService











        lookback = parse_int_param(






            request.args.get("lookback_days"),






            name="lookback_days",






            default=30,






            min_value=5,






            max_value=120,






        )











        dto = DataCoverageService(stock_service).assess_symbol(






            symbol,






            parse_market(market),








            lookback_days=lookback,






        )











        return ok_response(






            data=dto.model_dump(),






            legacy_alias_key=None,






            enable_legacy_alias=legacy,






        )
