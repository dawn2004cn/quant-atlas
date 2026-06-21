"""Historical resonance API route — TemporalKG similarity search.

Endpoints:
- POST /api/v1/historical-resonance/resonance — "这段走势与历史哪一刻最像？"
- GET  /api/v1/historical-resonance/stats — 知识库统计
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.domain.enums import MarketCode
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response

logger = get_logger(__name__)


def _get_kg():
    from app.modules.data.services.temporal_kg import get_temporal_kg

    return get_temporal_kg()


def _get_stock_service():
    from app.modules.market_data.services.stock_service import StockApplicationService
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

    provider = get_market_data_provider()
    return StockApplicationService(market_provider=provider)


def _register_historical_resonance_routes(blueprint: Blueprint, ctx=None) -> None:
    _ = ctx
    hr_bp = Blueprint("historical_resonance", __name__, url_prefix="/historical-resonance")

    @hr_bp.route("/resonance", methods=["POST"])
    def historical_resonance():
        """Find historical moments most similar to the current/selected bars."""
        body = request.get_json(silent=True) or {}
        symbol = body.get("symbol", "")
        if not symbol:
            payload = error_payload(ErrorCode.SYMBOL_REQUIRED, "symbol required")
            return jsonify(payload), ErrorCode.SYMBOL_REQUIRED.http_status

        market_str = body.get("market", "CN").upper()
        try:
            market = MarketCode(market_str)
        except ValueError:
            payload = error_payload(ErrorCode.VALIDATION_ERROR, f"invalid market: {market_str}")
            return jsonify(payload), ErrorCode.VALIDATION_ERROR.http_status

        start = body.get("start", "")
        end = body.get("end", "")
        top_k = min(body.get("top_k", 5), 10)

        stock_svc = _get_stock_service()
        bars = stock_svc.get_history(symbol, market, start, end)
        if not bars or len(bars) < 5:
            payload = error_payload(
                ErrorCode.VALIDATION_ERROR,
                "insufficient bars",
                details={"bar_count": len(bars) if bars else 0},
            )
            return jsonify(payload), ErrorCode.VALIDATION_ERROR.http_status

        kg = _get_kg()
        results = kg.resonance(symbol, bars, top_k=top_k)

        return success_response(
            data={
                "symbol": symbol,
                "bar_count": len(bars),
                "matches": [
                    {
                        "window_start": r.window_start,
                        "window_end": r.window_end,
                        "similarity": r.similarity,
                        "context": r.context,
                        "outcome_summary": r.outcome_summary,
                        "confidence_pct": r.confidence_pct,
                    }
                    for r in results
                ],
            },
        )

    @hr_bp.route("/stats", methods=["GET"])
    def resonance_stats():
        """Knowledge base statistics."""
        kg = _get_kg()
        return success_response(data=kg.stats())

    blueprint.register_blueprint(hr_bp)


@register_routes(name="historical_resonance", context="data", description="TemporalKG historical resonance")
def register_historical_resonance_routes(blueprint: Blueprint, ctx=None) -> None:
    _register_historical_resonance_routes(blueprint, ctx)
