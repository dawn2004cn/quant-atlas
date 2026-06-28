from __future__ import annotations

"""Trading preflight API for UI order confirmation."""

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.core.registry import register_routes
from app.modules.execution.services.pre_trade_preflight_service import PreTradePreflightService

from .common import ok_response
from .request_parsers import parse_float_param, parse_int_param
from .v1_context import ApiV1Context


@register_routes
def register_trading_preflight_routes(blueprint: Blueprint, ctx: ApiV1Context | None = None) -> None:
    del ctx
    service = PreTradePreflightService()

    @blueprint.post("/trading/preflight")
    @login_required
    def trading_preflight():
        """Pre-trade validation preview with risk score for UI modals."""
        body = request.get_json(silent=True) or {}
        symbol = str(body.get("symbol") or request.args.get("symbol") or "").strip()
        direction = str(body.get("direction") or body.get("side") or "BUY").strip()
        price = parse_float_param(body.get("price"), name="price", default=0.0)
        quantity = parse_int_param(body.get("quantity"), name="quantity", default=0)
        strategy_id = str(body.get("strategy_id") or body.get("strategy") or "manual").strip()
        account_equity = parse_float_param(body.get("account_equity"), name="account_equity", default=0.0)
        portfolio_value = parse_float_param(body.get("portfolio_value"), name="portfolio_value", default=0.0)
        current_position_pct = parse_float_param(
            body.get("current_position_pct"), name="current_position_pct", default=0.0
        )
        current_sector_pct = parse_float_param(
            body.get("current_sector_pct"), name="current_sector_pct", default=0.0
        )
        sector = str(body.get("sector") or "unknown").strip()
        if not symbol:
            raise ValidationError("symbol_required")

        result = service.preflight(
            symbol=symbol,
            direction=direction,
            price=price,
            quantity=quantity,
            strategy_id=strategy_id,
            account_equity=account_equity,
            portfolio_value=portfolio_value,
            sector=sector,
            current_position_pct=current_position_pct,
            current_sector_pct=current_sector_pct,
        )
        return ok_response(data=result.model_dump(mode="json"), passed=result.passed, ok=True, status="success")

    @blueprint.get("/strategy/copilot/preflight")
    @login_required
    def strategy_copilot_preflight():
        """Query-string preflight for strategy copilot quick actions."""
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        price = parse_float_param(request.args.get("price"), name="price", default=0.0)
        quantity = parse_int_param(request.args.get("quantity"), name="quantity", default=100)
        strategy_id = (request.args.get("strategy_id") or "trend_following").strip()
        direction = (request.args.get("direction") or "BUY").strip()
        account_equity = parse_float_param(request.args.get("account_equity"), name="account_equity", default=0.0)
        portfolio_value = parse_float_param(request.args.get("portfolio_value"), name="portfolio_value", default=0.0)
        sector = (request.args.get("sector") or "unknown").strip()
        result = service.preflight(
            symbol=symbol,
            direction=direction,
            price=price,
            quantity=quantity,
            strategy_id=strategy_id,
            account_equity=account_equity,
            portfolio_value=portfolio_value,
            sector=sector,
        )
        return ok_response(data=result.model_dump(mode="json"), passed=result.passed, ok=True, status="success")
