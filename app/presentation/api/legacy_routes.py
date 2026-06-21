from __future__ import annotations
"""Legacy API compatibility layer for non-migrated clients.

Primary application flows now use ``/api/v1/*``. This module keeps only a
small deprecated route surface during the migration period.
"""


from flask import Blueprint, request
from .common import ok_response, ok_resource
from flask_login import login_required

from ...core.middleware.request_context import require_authenticated_user_id
from ...domain.enums import MarketCode
from ...domain.dto.quote_factory import canonical_quote_payload, canonical_panorama_dict


def _uid() -> int:
    return require_authenticated_user_id()


def create_legacy_api_blueprint(
    market_service,
    stock_service,
    strategy_service,
    watchlist_service,
    stock_group_service,
    user_service,
):
    """Expose a minimal deprecated route set."""
    del stock_group_service, user_service
    blueprint = Blueprint("legacy_api", __name__, url_prefix="/api")

    @blueprint.get("/stocks")
    @login_required
    def stocks():
        from app.domain.dto.quote_factory import canonical_quote_list

        symbols = watchlist_service.list_symbols(user_id=_uid())
        quotes = market_service.list_quotes(MarketCode.CN, symbols)
        return ok_response(data=canonical_quote_list(quotes, market="CN"))

    @blueprint.get("/stock/<symbol>")
    @login_required
    def stock(symbol: str):
        detail = stock_service.get_stock_detail(symbol, MarketCode.CN)
        profile = detail.get("profile", {})
        realtime = profile.get("realtime", {})
        merged = canonical_quote_payload(
            {
                "code": symbol,
                "name": realtime.get("name") or profile.get("detail", {}).get("name", symbol),
                "price": realtime.get("price") or profile.get("detail", {}).get("price", 0),
                "change_pct": realtime.get("change_pct") or profile.get("detail", {}).get("change_pct", 0),
                "change_amount": realtime.get("change_amount")
                or profile.get("detail", {}).get("change_amount", 0),
            },
            market="CN",
        )
        return ok_response(data=merged)

    @blueprint.get("/history/<symbol>")
    @login_required
    def history(symbol: str):
        start = request.args.get("start", "")
        end = request.args.get("end", "")
        if not start or not end:
            from app.core.utils.datetime_utils import default_history_window

            start, end = default_history_window()
        history_payload = stock_service.get_history(symbol, MarketCode.CN, start, end)
        return ok_response(data=history_payload["history"])

    @blueprint.post("/backtest")
    @login_required
    def backtest():
        payload = request.get_json(silent=True) or {}
        result = strategy_service.backtest(
            symbol=payload.get("symbol", ""),
            strategy_name=payload.get("strategy", "MA"),
            start=payload.get("start") or payload.get("start_date", ""),
            end=payload.get("end") or payload.get("end_date", ""),
            initial_capital=float(payload.get("initial_capital", 100000)),
        )
        return ok_response(data={"metrics": result.get("metrics", {}), "trades": result.get("trades", [])})

    @blueprint.get("/watchlist")
    @login_required
    def watchlist():
        symbols = watchlist_service.list_symbols(user_id=_uid())
        quotes = market_service.list_quotes(MarketCode.CN, symbols)
        return ok_response(data=quotes)

    @blueprint.post("/watchlist")
    @login_required
    def add_watchlist():
        payload = request.get_json(silent=True) or {}
        symbol = payload.get("symbol") or payload.get("code", "")
        watchlist_service.add_symbol(_uid(), symbol)
        return ok_response(data={"message": "添加成功"})

    @blueprint.delete("/watchlist/<symbol>")
    @login_required
    def remove_watchlist(symbol: str):
        watchlist_service.remove_symbol(_uid(), symbol)
        return ok_response(data={"message": "移除成功"})

    @blueprint.get("/market/sentiment")
    @login_required
    def market_sentiment():
        sentiment = market_service.get_sentiment(MarketCode.CN) if market_service else None
        return ok_response(data=sentiment or {})

    @blueprint.get("/market/movements")
    @login_required
    def market_movements():
        movements = market_service.get_movements(MarketCode.CN, top_n=20) if market_service else []
        return ok_response(data={"movements": movements})

    @blueprint.get("/market-rankings")
    @login_required
    def market_rankings():
        if not market_service:
            return ok_response(data={"rankings": {}, "summary": {}})
        panorama = market_service.get_panorama(MarketCode.CN)
        panorama_dict = panorama.model_dump() if hasattr(panorama, "model_dump") else {}
        panorama_dict = canonical_panorama_dict(panorama_dict, market="CN")
        return ok_response(
            data={
                "rankings": {
                    "gainers": panorama_dict.get("gainers", []),
                    "losers": panorama_dict.get("losers", []),
                    "amounts": panorama_dict.get("amounts", []),
                    "turnovers": panorama_dict.get("turnovers", []),
                },
                "summary": panorama_dict.get("summary") or {},
                "sectors": panorama_dict.get("sectors") or [],
                "updated_at": panorama_dict.get("updated_at") or panorama_dict.get("timestamp"),
            }
        )

    return blueprint

