from __future__ import annotations

from flask import Blueprint
from flask_login import login_required

from ...application.errors import NotFoundError
from .common import ok_response
from ...application.request_executor import run_async
from .v1_context import ApiV1Context
from app.core.registry import register_routes


@register_routes(name="ten_kings", context="strategy", description="天王狙击系统仪表盘")
def register_ten_kings_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
) -> None:
    def _svc():
        svc = getattr(ctx, "ten_kings_sniper_service", None)
        if svc is None:
            from ...application.errors import ValidationError
            raise ValidationError("ten_kings_sniper_service_unavailable")
        return svc

    @blueprint.get("/ten-kings/dashboard")
    @login_required
    def get_ten_kings_dashboard():
        """获取天王狙击系统仪表盘数据。"""
        svc = _svc()
        holdings = svc.list_active_holdings()
        return ok_response(
            data={
                "capital_initial": 500000.0,
                "holdings": [
                    {
                        "symbol": h.symbol,
                        "name": h.name,
                        "strategy": h.strategy_name,
                        "price_entry": h.initial_price,
                        "price_current": h.current_price,
                        "pnl_pct": h.pnl_pct,
                        "status": h.status,
                    }
                    for h in holdings
                ],
                "market_regime": "SIDEWAYS",
            }
        )

    @blueprint.get("/ten-kings/selection/<int:selection_id>")
    @login_required
    def get_selection_detail(selection_id: int):
        """获取某次选股的详细投委会意见。"""
        svc = _svc()
        detail = svc.get_selection_detail(selection_id)
        if detail is None:
            raise NotFoundError(
                "selection_not_found",
                details={"selection_id": selection_id},
            )
        return ok_response(data=detail)

    @blueprint.post("/ten-kings/scan")
    @login_required
    def trigger_scan():
        """手动触发每日扫描。"""
        svc = _svc()
        res = run_async(svc.run_daily_scan())
        return ok_response(data=res)
