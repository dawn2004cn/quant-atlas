"""Watchlist CRUD, export, quotes, and price alerts."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ExternalServiceError, ValidationError
from app.domain.enums import MarketCode
from app.presentation.api.common import ok_collection, ok_resource, ok_response
from app.presentation.api.v1.portfolio_users.runtime import PortfolioUserRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_portfolio_watchlist_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None,
    *,
    runtime: PortfolioUserRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    def _watchlist_svc():
        svc = runtime.watchlist_service
        if svc is None:
            raise ExternalServiceError(
                "watchlist_service_unavailable",
                details={"reason": "Watchlist service is not configured"},
            )
        return svc

    def _market_svc():
        return runtime.market_service

    @blueprint.get("/watchlist")
    @login_required
    def watchlist():
        symbols = _watchlist_svc().list_symbols(user_id=runtime.user_id())
        return ok_collection(items=symbols, item_key="symbols", enable_legacy_alias=legacy)

    @blueprint.get("/watchlist/details")
    @login_required
    def watchlist_details():
        symbols = _watchlist_svc().list_symbols(user_id=runtime.user_id())
        market_service = _market_svc()
        stocks = market_service.list_quotes(MarketCode.CN, symbols) if market_service else []
        return ok_collection(
            items=stocks,
            item_key="stocks",
            enable_legacy_alias=legacy,
            symbols=symbols,
        )

    @blueprint.get("/watchlist/snapshot")
    @login_required
    def watchlist_snapshot():
        symbols = _watchlist_svc().list_symbols(user_id=runtime.user_id())
        if not symbols:
            return ok_response(data={"stocks": [], "summary": {}}, legacy_alias_key=None)
        market_service = _market_svc()
        stocks = market_service.list_quotes(MarketCode.CN, symbols) if market_service else []
        summary = {
            "total": len(stocks),
            "up": sum(1 for s in stocks if float(s.get("change_pct", 0) or 0) > 0),
            "down": sum(1 for s in stocks if float(s.get("change_pct", 0) or 0) < 0),
            "flat": sum(1 for s in stocks if float(s.get("change_pct", 0) or 0) == 0),
            "total_change": sum(float(s.get("change_pct", 0) or 0) for s in stocks),
        }
        light_stocks = [
            {
                "code": s.get("code", s.get("symbol", "")),
                "name": s.get("name", ""),
                "price": s.get("price", 0),
                "change_pct": s.get("change_pct", 0),
                "industry": s.get("industry", ""),
            }
            for s in stocks
        ]
        return ok_response(
            data={"stocks": light_stocks, "summary": summary},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/watchlist")
    @login_required
    def add_watchlist():
        payload = request.get_json(silent=True) or {}
        sym = payload.get("symbol", "")
        symbols = _watchlist_svc().add_symbol(runtime.user_id(), sym)
        runtime.record_audit("watchlist_add", "symbol", str(sym))
        runtime.psychology_after_watchlist("add", str(sym))
        return ok_collection(items=symbols, item_key="symbols", enable_legacy_alias=legacy)

    @blueprint.delete("/watchlist/<symbol>")
    @login_required
    def remove_watchlist(symbol: str):
        symbols = _watchlist_svc().remove_symbol(runtime.user_id(), symbol)
        runtime.record_audit("watchlist_remove", "symbol", str(symbol))
        runtime.psychology_after_watchlist("remove", str(symbol))
        return ok_collection(items=symbols, item_key="symbols", enable_legacy_alias=legacy)

    @blueprint.post("/watchlist/batch-add")
    @login_required
    def batch_add_watchlist():
        payload = request.get_json(silent=True) or {}
        symbols = payload.get("symbols", [])
        success, message, symbols = _watchlist_svc().batch_add_symbols(runtime.user_id(), symbols)
        runtime.require_ok(success, message, code="watchlist_batch_add_failed")
        return ok_collection(items=symbols, item_key="symbols", enable_legacy_alias=legacy, message=message)

    @blueprint.post("/watchlist/batch-remove")
    @login_required
    def batch_remove_watchlist():
        payload = request.get_json(silent=True) or {}
        symbols = payload.get("symbols", [])
        success, message, symbols = _watchlist_svc().batch_remove_symbols(runtime.user_id(), symbols)
        runtime.require_ok(success, message, code="watchlist_batch_remove_failed")
        return ok_collection(items=symbols, item_key="symbols", enable_legacy_alias=legacy, message=message)

    @blueprint.post("/watchlist/create")
    @login_required
    def create_watchlist():
        payload = request.get_json(silent=True) or {}
        success, message, group = _watchlist_svc().create_watchlist(
            runtime.user_id(),
            payload.get("name", "").strip(),
            payload.get("description", "").strip(),
        )
        runtime.require_ok(success, message, code="watchlist_create_failed")
        return ok_resource(resource=group, resource_key="watchlist", enable_legacy_alias=legacy, message=message)

    @blueprint.delete("/watchlist/name/<name>")
    @login_required
    def delete_watchlist(name: str):
        success, message = _watchlist_svc().delete_watchlist(runtime.user_id(), name)
        runtime.require_ok(success, message, code="watchlist_delete_failed")
        return ok_response(message=message, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/watchlist/export/blk")
    @login_required
    def export_watchlist_blk():
        group_name = request.args.get("group", "").strip() or None
        success, message, content = _watchlist_svc().export_to_blk(runtime.user_id(), group_name=group_name)
        runtime.require_ok(success, message, code="watchlist_export_blk_failed")
        return ok_response(
            data={"content": content, "filename": f"{(group_name or 'watchlist')}.blk"},
            legacy_alias_key=None,
            message=message,
        )

    @blueprint.get("/watchlist/export/csv")
    @login_required
    def export_watchlist_csv():
        group_name = request.args.get("group", "").strip() or None
        success, message, content = _watchlist_svc().export_to_csv(runtime.user_id(), group_name=group_name)
        runtime.require_ok(success, message, code="watchlist_export_csv_failed")
        return ok_response(
            data={"content": content, "filename": f"{(group_name or 'watchlist')}.csv"},
            enable_legacy_alias=False,
            message=message,
        )

    @blueprint.get("/watchlist/quotes")
    @login_required
    def watchlist_quotes():
        group_name = request.args.get("group", "").strip() or None
        sort_by = request.args.get("sort", "add_time").strip()
        ascending = request.args.get("order", "asc").strip().lower() == "asc"
        try:
            page = int(request.args.get("page") or 1)
            page = max(1, page)
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = int(request.args.get("page_size") or 50)
            page_size = max(1, min(200, page_size))
        except (ValueError, TypeError):
            page_size = 50
        valid_sorts = ["add_time", "change_pct", "price", "name", "industry"]
        if sort_by not in valid_sorts:
            sort_by = "add_time"
        from app.modules.market_data.services.watchlist_service import SortBy

        result = _watchlist_svc().get_sorted_quotes(
            runtime.user_id(),
            group_name=group_name,
            sort_by=SortBy(sort_by),
            ascending=ascending,
            page=page,
            page_size=page_size,
        )
        return ok_response(
            data={"stocks": result["items"]},
            legacy_alias_key="stocks",
            enable_legacy_alias=legacy,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            pages=result["pages"],
        )

    @blueprint.post("/watchlist/alerts")
    @login_required
    def add_price_alert():
        payload = request.get_json(silent=True) or {}
        symbol = payload.get("symbol", "").strip()
        alert_type = payload.get("type", "above").strip()
        threshold = float(payload.get("threshold", 0))
        if not symbol:
            raise ValidationError("symbol_required", details={"reason": "股票代码不能为空"})
        success, message = _watchlist_svc().add_price_alert(
            runtime.user_id(),
            symbol,
            alert_type,
            threshold,
        )
        runtime.require_ok(success, message, code="watchlist_alert_add_failed")
        return ok_response(message=message, legacy_alias_key=None)

    @blueprint.delete("/watchlist/alerts/<symbol>/<alert_type>")
    @login_required
    def remove_price_alert(symbol: str, alert_type: str):
        success, message = _watchlist_svc().remove_price_alert(runtime.user_id(), symbol, alert_type)
        runtime.require_ok(success, message, code="watchlist_alert_remove_failed")
        return ok_response(message=message, legacy_alias_key=None)

    @blueprint.get("/watchlist/alerts")
    @login_required
    def get_price_alerts():
        alerts = _watchlist_svc().get_price_alerts(runtime.user_id())
        triggered = _watchlist_svc().check_price_alerts(runtime.user_id())
        return ok_response(
            data={"alerts": alerts, "triggered": triggered},
            legacy_alias_key=None,
            count=len(alerts),
        )
