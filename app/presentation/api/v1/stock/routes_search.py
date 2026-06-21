from __future__ import annotations
from flask import Blueprint
from flask_login import login_required
from pydantic import BaseModel, Field
from app.core.registry import register_routes
from ...v1_context import ApiV1Context
from ...common import ok_response, parse_market
from ...decorators import service_fallback
from ...dto_validation import validate_request
from .....application.dto.market_data_dto import StockHistoryDTO as StockHistoryRequest


class StockSearchRequest(BaseModel):
    """Query DTO for /api/v1/stocks/search."""

    q: str = Field(default="")
    market: str = Field(default="CN")
    limit: int = Field(default=20, ge=1, le=200)
    tags: str = Field(default="")
    mode: str = Field(default="search")
    strict: str = Field(default="")

@register_routes(name="stock_search", context="market_data", description="Stock search")
def register_stock_search(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields
    stock_service = ctx.stock_service

    @blueprint.get("/stocks/search")





    @login_required





    @validate_request(StockSearchRequest, source="args")
    @service_fallback("stock_service")





    def stock_search(req: StockSearchRequest):






        query = req.q.strip()





        limit = req.limit





        market = req.market.strip().upper()





        tags = [





            t.strip()





            for t in (req.tags or "").replace("+", ",").split(",")





            if t.strip()





        ]





        mode = req.mode.strip().lower()





        strict = req.strict.strip().lower() in {"1", "true", "yes"}





        if not query and not tags:





            return ok_response(data={"stocks": []}, legacy_alias_key=None, enable_legacy_alias=legacy, count=0)





        if mode == "discover" or tags:





            from app.modules.system.services.ui.stock_discovery_service import StockDiscoveryService











            payload = StockDiscoveryService(stock_service).discover(





                query,





                tags=tags,





                limit=limit,





                market=parse_market(market),





                strict=strict,





            )





            return ok_response(





                data=payload,





                legacy_alias_key=None,





                enable_legacy_alias=legacy,





                count=len(payload["stocks"]),





            )





        results = stock_service.search_stocks(query, limit=limit, market=parse_market(market))





        return ok_response(data={"stocks": results}, legacy_alias_key=None, enable_legacy_alias=legacy, count=len(results))
