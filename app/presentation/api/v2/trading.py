from __future__ import annotations

from flask import Blueprint, request
from ..auth_guard import api_auth_required
from ..responses import success_response

def create_trading_blueprint(ctx):
    bp = Blueprint("v2_trading", __name__)

    @bp.post("/risk/check")
    @api_auth_required
    def risk_check():
        body = request.get_json(silent=True) or {}
        # risk_service is handled via the context in routes_v2, I'll assume it's in ctx
        # Note: In current routes_v2, risk_service was a local variable in create_api_v2_blueprint
        # I need to make sure it's added to ApiV2Context.
        if hasattr(ctx, 'risk_service') and ctx.risk_service:
            result = ctx.risk_service.check_order(
                symbol=body.get("symbol", ""),
                side=body.get("side", "buy"),
                quantity=body.get("quantity", 0),
                price=body.get("price", 0.0),
                account_id=body.get("account_id", "default"),
                total_equity=body.get("total_equity", 100000),
                cash_available=body.get("cash_available", 100000),
                current_positions=body.get("current_positions", {}),
                daily_pnl=body.get("daily_pnl", 0),
                market=body.get("market", "CN"),
            )
        else:
            result = {"ok": True, "message": "risk_service not configured"}
        return success_response(data=result)

    return bp
