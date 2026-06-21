from __future__ import annotations

from flask import Blueprint, request
from ..auth_guard import api_auth_required
from ..responses import success_response
from app.core.composite_rate_limiter import LimitRule, require_rate_limit

def create_ai_blueprint(ctx):
    bp = Blueprint("v2_ai", __name__)

    @bp.post("/predictions")
    @api_auth_required
    @require_rate_limit(
        LimitRule(max_calls=10, window_seconds=60, key_prefix="ai_prediction"),
    )
    def run_prediction():
        from .request_parsers import parse_dto
        from ....application.dto.v2_dtos import PredictionRequestDTO
        body = request.get_json(silent=True) or {}
        if ctx.enable_dto_validation:
            dto = parse_dto(body, PredictionRequestDTO)
            result = ctx.prediction_service.predict(
                symbol=dto.symbol,
                market=dto.market if hasattr(dto, 'market') else "CN",
                horizon=getattr(dto, 'horizon', 10),
            )
        else:
            result = ctx.prediction_service.predict(
                symbol=body.get("symbol", ""),
                market=body.get("market", "CN"),
                horizon=int(body.get("horizon", 10)),
            )
        return success_response(data=result)

    @bp.post("/analysis/ai")
    @api_auth_required
    def ai_analysis():
        body = request.get_json(silent=True) or {}
        symbol = body.get("symbol", "")
        market = body.get("market", "CN")
        if ctx.ai_facade is not None:
            result = ctx.ai_facade.analyze(
                symbol,
                market,
                user_hypothesis=body.get("user_hypothesis"),
                hypothesis_id=body.get("hypothesis_id"),
            )
        else:
            from ....domain.enums import MarketCode
            try:
                mc = MarketCode(market.upper())
            except ValueError:
                mc = MarketCode.CN
            result = ctx.ai_analysis_service.analyze(symbol, mc)
        return success_response(data=result, meta={"symbol": symbol})

    @bp.post("/analysis/ai/deep")
    @api_auth_required
    def ai_deep_analysis():
        body = request.get_json(silent=True) or {}
        symbol = body.get("symbol", "")
        market = body.get("market", "CN")
        if ctx.ai_facade is not None:
            result = ctx.ai_facade.analyze(
                symbol,
                market,
                user_hypothesis=body.get("user_hypothesis"),
                hypothesis_id=body.get("hypothesis_id"),
                depth="deep",
            )
        else:
            from ....domain.enums import MarketCode
            try:
                mc = MarketCode(market.upper())
            except ValueError:
                mc = MarketCode.CN
            depth = body.get("depth", "standard")
            if depth == "deep" and hasattr(ctx.ai_analysis_service, "deep_analyze"):
                result = ctx.ai_analysis_service.deep_analyze(symbol, mc, depth=depth)
            else:
                result = ctx.ai_analysis_service.analyze(symbol, mc)
        return success_response(data=result, meta={"symbol": symbol})

    @bp.post("/research")
    @api_auth_required
    @require_rate_limit(
        LimitRule(max_calls=3, window_seconds=60, key_prefix="ai_research"),
    )
    def run_research():
        body = request.get_json(silent=True) or {}
        ticker = body.get("ticker", "")
        query = body.get("query", "")
        user_id = body.get("user_id", 0)
        result = ctx.ai_research_service.run_research(ticker, query, user_id)
        return success_response(data=result)

    return bp
