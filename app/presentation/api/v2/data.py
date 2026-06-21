from __future__ import annotations

from flask import Blueprint, request
from ..auth_guard import api_auth_required
from ....domain.enums import MarketCode
from ..responses import success_response

def create_data_blueprint(ctx):
    bp = Blueprint("v2_data", __name__)

    @bp.get("/news/<symbol>")
    @api_auth_required
    def get_news(symbol: str):
        from .request_parsers import parse_dto
        from ....application.dto.v2_dtos import NewsRequestDTO
        body = request.get_json(silent=True) or request.args.to_dict()
        if ctx.enable_dto_validation:
            dto = parse_dto(body, NewsRequestDTO, partial=True)
            count = getattr(dto, 'count', 20)
        else:
            count = int(body.get("count", 20))
        news = ctx.news_provider.get_news(symbol, count=count)
        return success_response(data=news, meta={"symbol": symbol})

    @bp.get("/pool")
    @api_auth_required
    def get_pool():
        market = request.args.get("market", "CN")
        try:
            mc = MarketCode(market.upper())
        except ValueError:
            from ....application.errors import ValidationError
            raise ValidationError(f"Invalid market: {market}")
        top_n = int(request.args.get("top_n", 20))
        result = ctx.pool_service.get_live_pool(mc, top_n)
        return success_response(data=result)

    @bp.get("/signals")
    @api_auth_required
    def list_signals():
        if ctx.signal_flag_service:
            market = request.args.get("market", "CN")
            try:
                mc = MarketCode(market.upper())
            except ValueError:
                mc = MarketCode.CN
            result = ctx.signal_flag_service.get_flag_pool(mc)
        else:
            result = {"candidates": []}
        return success_response(data=result)

    return bp
