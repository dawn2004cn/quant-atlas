from __future__ import annotations

"""Stock price resonance route."""

from flask import Blueprint, request
from flask_login import login_required

from app.core.logger import get_logger
from app.core.registry import register_routes
from ...common import ok_response, parse_market
from ...decorators import service_fallback

logger = get_logger(__name__)


@register_routes(name="stock_price", context="market_data", description="Stock price resonance meter")
def register_stock_price(blueprint: Blueprint, ctx) -> None:

    legacy = ctx.enable_legacy_response_fields
    stock_service = ctx.stock_service

    @blueprint.get("/stocks/<market>/<symbol>/resonance")
    @login_required
    @service_fallback("stock_service")
    def stock_resonance(market: str, symbol: str):

        """Technical indicator resonance meter (MACD/KDJ/RSI/MA)."""

        from datetime import date, timedelta

        from app.modules.strategy.services.analytics.visual_data_reducer_service import (
            TechnicalResonanceMeter,
        )

        try:
            from app.infrastructure.providers.rust_indicators import RustIndicatorProvider as _IndicatorImpl
        except Exception:
            _IndicatorImpl = None

        m = parse_market(market)

        end_d = date.today()

        start_d = end_d - timedelta(days=120)

        try:

            history = stock_service.get_history(
                symbol, m, start_d.isoformat(), end_d.isoformat()
            )

            items = history if isinstance(history, list) else (history or {}).get("history", [])

        except Exception as exc:  # noqa: BLE001

            logger.warning("stock_resonance history error %s: %s", symbol, exc)

            items = []

        payload = TechnicalResonanceMeter((_IndicatorImpl() if _IndicatorImpl else None)).calculate_resonance(items)

        payload["symbol"] = symbol.upper()

        payload["market"] = m.value

        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
