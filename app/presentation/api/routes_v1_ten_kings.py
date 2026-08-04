from __future__ import annotations

from flask import Blueprint
from flask_login import login_required

from app.core.registry import register_routes

from ...application.errors import NotFoundError
from ...application.request_executor import run_async
from .common import ok_response
from .decorators import service_fallback
from .v1_context import ApiV1Context


@register_routes(name="ten_kings", context="strategy", description="天王狙击系统仪表盘")
def register_ten_kings_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
) -> None:
    legacy = bool(ctx.enable_legacy_response_fields) if ctx is not None else False

    @blueprint.get("/ten-kings/dashboard")
    @login_required
    @service_fallback("ten_kings_sniper_service")
    def get_ten_kings_dashboard():
        """获取天王狙击系统仪表盘数据。"""
        svc = getattr(ctx, "ten_kings_sniper_service", None)
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
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/ten-kings/selection/<int:selection_id>")
    @login_required
    @service_fallback("ten_kings_sniper_service")
    def get_selection_detail(selection_id: int):
        """获取某次选股的详细投委会意见。"""
        svc = getattr(ctx, "ten_kings_sniper_service", None)
        detail = svc.get_selection_detail(selection_id)
        if detail is None:
            raise NotFoundError(
                "selection_not_found",
                details={"selection_id": selection_id},
            )
        return ok_response(
            data=detail,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/ten-kings/scan")
    @login_required
    @service_fallback("ten_kings_sniper_service")
    def trigger_scan():
        """手动触发每日扫描。"""
        svc = getattr(ctx, "ten_kings_sniper_service", None)
        res = run_async(svc.run_daily_scan())
        return ok_response(
            data=res,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
