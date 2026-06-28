from __future__ import annotations
from flask import Blueprint
from flask_login import login_required
from pydantic import BaseModel, Field, field_validator
from app.application.errors import ValidationError
from app.core.registry import register_routes
from ...v1_context import ApiV1Context
from ...common import ok_resource, parse_market
from ...decorators import service_fallback
from ...dto_validation import validate_request
from ...stock_route_helpers import enrich_quote_resource


class StockQuoteRequest(BaseModel):
    """Query DTO for /api/v1/quotes (single-symbol stock detail lookup)."""

    symbol: str = Field(min_length=1, max_length=32)
    market: str = Field(default="CN")

    @field_validator("symbol")
    @classmethod
    def _strip_symbol(cls, v: str) -> str:
        return v.strip()

    @field_validator("market")
    @classmethod
    def _normalize_market(cls, v: str) -> str:
        return v.strip().upper()

@register_routes(name="stock_quote", context="market_data", description="Stock quotes")
def register_stock_quote(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    stock_service = ctx.stock_service

    @blueprint.get("/quotes")





    @login_required





    @validate_request(StockQuoteRequest, source="args")
    @service_fallback("stock_service")
    def stock_quote(req: StockQuoteRequest):






        symbol = req.symbol.strip()





        market = req.market.strip().upper()





        try:





            market_code = parse_market(market)





            detail = stock_service.get_stock_detail(symbol, market_code)





            if isinstance(detail, dict):





                profile = detail.get("profile", {})





                realtime = profile.get("realtime", {}) if isinstance(profile, dict) else {}





                quote = enrich_quote_resource(





                    {





                        "symbol": detail.get("symbol", symbol),





                        "name": realtime.get("name", detail.get("symbol", symbol)),





                        "price": realtime.get("price", 0),





                        "change_pct": realtime.get("change_pct", 0),





                        "change": realtime.get("change_amount", 0),





                        "volume": realtime.get("volume", 0),





                        "market": market,





                        "quote_time": realtime.get("quote_time") or realtime.get("updated_at"),





                    },





                    source="stock_quote",





                )





                return ok_resource(





                    resource=quote,





                    resource_key="quote",





                    enable_legacy_alias=True,





                )





            realtime = detail.profile.get("realtime", {})





            quote = enrich_quote_resource(





                {





                    "symbol": detail.code,





                    "name": realtime.get("name", detail.code or symbol),





                    "price": realtime.get("price", 0),





                    "change_pct": realtime.get("change_pct", 0),





                    "change": realtime.get("change_amount", 0),





                    "volume": realtime.get("volume", 0),





                    "market": market,





                    "quote_time": realtime.get("quote_time") or realtime.get("updated_at"),





                },





                source="stock_quote",





            )





            return ok_resource(





                resource=quote,





                resource_key="quote",





                enable_legacy_alias=True,





            )





        except Exception as e:





            raise ValidationError(f"Failed to get quote: {str(e)}")
