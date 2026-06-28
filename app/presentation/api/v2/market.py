from __future__ import annotations

from flask import Blueprint, request

from ....application.errors import ValidationError
from ....domain.dto.quote_factory import canonical_panorama_dict
from ....domain.enums import MarketCode
from ..auth_guard import api_auth_required
from ..responses import success_response


def create_market_blueprint(ctx):
    bp = Blueprint("v2_market", __name__)

    @bp.get("/markets/panorama/<market>")
    def market_panorama(market: str):
        try:
            mc = MarketCode(str(market).upper())
        except ValueError:
            raise ValidationError(f"Invalid market: {market}") from None
        if ctx.market_facade is not None:
            panorama_dict = ctx.market_facade.get_panorama(mc)
        else:
            panorama = ctx.market_service.get_panorama(mc)
            panorama_dict = panorama if isinstance(panorama, dict) else panorama.model_dump()
        panorama_dict = canonical_panorama_dict(panorama_dict, market=mc.value)
        return success_response(data=panorama_dict, meta={"market": mc.value})

    @bp.get("/stocks/<symbol>")
    @api_auth_required
    def stock_detail(symbol: str):
        market = request.args.get("market", "CN")
        try:
            mc = MarketCode(market.upper())
        except ValueError:
            raise ValidationError(f"Invalid market: {market}") from None
        profile = ctx.stock_service.get_stock_detail(symbol, mc)
        if hasattr(profile, "to_dict"):
            payload = profile.to_dict()
        elif hasattr(profile, "model_dump"):
            payload = profile.model_dump()
        else:
            payload = profile if isinstance(profile, dict) else {"profile": profile}
        return success_response(
            data=payload,
            meta={"symbol": symbol, "market": mc.value},
        )

    @bp.get("/stocks")
    @api_auth_required
    def stock_search():
        from ....application.dto.v2_dtos import StockSearchDTO
        from .request_parsers import parse_dto
        dto = parse_dto(request.args.to_dict(), StockSearchDTO, partial=True)
        results = ctx.stock_service.search_stocks(
            keyword=dto.keyword,
            market=dto.market if hasattr(dto, 'market') else MarketCode.CN,
            sector=dto.sector if hasattr(dto, 'sector') else None,
            limit=getattr(dto, 'limit', 20),
        )
        return success_response(data=results)

    @bp.get("/stocks/<symbol>/history")
    @api_auth_required
    def stock_history(symbol: str):
        from ....application.dto import StockHistoryDTO
        from .request_parsers import parse_dto
        dto = parse_dto(request.args.to_dict(), StockHistoryDTO, partial=True)
        try:
            mc = MarketCode(str(dto.market).upper())
        except (ValueError, AttributeError):
            mc = MarketCode.CN
        if ctx.market_facade is not None:
            bars = ctx.market_facade.get_history_bars(
                symbol=symbol,
                market=mc,
                start_date=getattr(dto, "start_date", None),
                end_date=getattr(dto, "end_date", None),
                count=getattr(dto, "count", 100),
            )
        else:
            bars = ctx.market_service.get_history_bars(
                symbol=symbol,
                market=mc,
                start_date=getattr(dto, 'start_date', None),
                end_date=getattr(dto, 'end_date', None),
                count=getattr(dto, 'count', 100),
            )
        return success_response(data=bars, meta={"symbol": symbol})

    @bp.get("/markets/history/<market>/<symbol>")
    @api_auth_required
    def market_history(symbol: str, market: str):
        try:
            mc = MarketCode(market.upper())
        except ValueError:
            raise ValidationError(f"Invalid market: {market}") from None
        if ctx.market_facade is not None:
            bars = ctx.market_facade.get_history_bars(
                symbol=symbol,
                market=mc,
                start_date=request.args.get("start_date"),
                end_date=request.args.get("end_date"),
            )
        else:
            bars = ctx.market_service.get_history_bars(
                symbol=symbol,
                market=mc,
                start_date=request.args.get("start_date"),
                end_date=request.args.get("end_date"),
            )
        return success_response(data=bars, meta={"symbol": symbol, "market": mc.value})

    return bp
