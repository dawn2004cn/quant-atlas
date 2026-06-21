"""Stock group management routes."""

from __future__ import annotations

import logging
import traceback

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import ExternalServiceError, ValidationError
from app.domain.enums import MarketCode
from app.presentation.api.common import ok_collection, ok_resource, ok_response
from app.presentation.api.v1.portfolio_users.runtime import PortfolioUserRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_portfolio_stock_group_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None,
    *,
    runtime: PortfolioUserRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/stock-groups")
    def stock_groups():
        """List stock groups - works without login for index page."""
        try:
            user_id = runtime.user_id() if current_user.is_authenticated else None
            if user_id is None:
                return ok_collection(items=[], item_key="groups", enable_legacy_alias=legacy)
            svc = runtime.stock_group_service
            if svc is None:
                from flask import jsonify
                return jsonify({"error": "stock_group_service_unavailable", "message": "Stock group service is not configured"}), 503
            groups = svc.list_groups(user_id=user_id)
            return ok_collection(items=groups, item_key="groups", enable_legacy_alias=legacy)
        except Exception:
            logger.exception("stock_groups failed: user_authenticated=%s", getattr(current_user, "is_authenticated", "n/a"))
            raise

    def _stock_group_svc():
        svc = runtime.stock_group_service
        if svc is None:
            raise ExternalServiceError("stock_group_service_unavailable", details={"reason": "Stock group service is not configured"})
        return svc

    @blueprint.post("/stock-groups")
    @login_required
    def create_stock_group():
        payload = request.get_json(silent=True) or {}
        success, message, group = _stock_group_svc().create_group(
            payload.get("name", "").strip(),
            payload.get("description", "").strip(),
            payload.get("color", "").strip(),
            user_id=runtime.user_id(),
        )
        runtime.require_ok(success, message, code="stock_group_create_failed")
        return ok_resource(
            resource=group,
            resource_key="group",
            enable_legacy_alias=legacy,
            message=message,
        )

    @blueprint.put("/stock-groups/<int:group_id>")
    @login_required
    def update_stock_group_with_color(group_id: int):
        payload = request.get_json(silent=True) or {}
        success, message = _stock_group_svc().update_group(
            group_id,
            payload.get("name", "").strip(),
            payload.get("description", "").strip(),
            payload.get("color", "").strip(),
            user_id=runtime.user_id(),
        )
        runtime.require_ok(success, message, code="stock_group_update_failed")
        return ok_response(message=message, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.delete("/stock-groups/<int:group_id>")
    @login_required
    def delete_stock_group(group_id: int):
        success, message = _stock_group_svc().delete_group(group_id, user_id=runtime.user_id())
        runtime.require_ok(success, message, code="stock_group_delete_failed")
        return ok_response(message=message, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/stock-groups/<int:group_id>/stocks")
    @login_required
    def group_stocks(group_id: int):
        try:
            logger.info("group_stocks start: group_id=%s", group_id)
            symbols = _stock_group_svc().list_group_symbols(group_id, user_id=runtime.user_id())
            if not symbols:
                return ok_collection(items=[], item_key="stocks", symbols=[], group_id=group_id)
            try:
                stocks = runtime.market_service.list_quotes(MarketCode.CN, symbols) if runtime.market_service else []
            except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
                logger.error("list_quotes error: %s", exc)
                traceback.print_exc()
                stocks = []
            return ok_collection(
                items=stocks,
                item_key="stocks",
                enable_legacy_alias=legacy,
                symbols=symbols,
                group_id=group_id,
            )
        except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
            logger.error("group_stocks error: %s", exc)
            traceback.print_exc()
            return ok_collection(items=[], item_key="stocks", symbols=[], group_id=group_id)

    @blueprint.post("/stock-groups/<int:group_id>/stocks")
    @login_required
    def add_group_stock(group_id: int):
        payload = request.get_json(silent=True) or {}
        symbol = payload.get("stock_code") or payload.get("symbol") or payload.get("code", "")
        if not symbol:
            raise ValidationError("symbol_required", details={"reason": "股票代码不能为空"})
        try:
            success, message = _stock_group_svc().add_symbol(group_id, symbol, user_id=runtime.user_id())
            if success:
                runtime.record_audit("add_watchlist", "stock", symbol, {"group_id": group_id})
            else:
                logger.warning("add_group_stock failed: group_id=%s, symbol=%s, message=%s", group_id, symbol, message)
            runtime.require_ok(success, message, code="stock_group_add_symbol_failed")
            return ok_response(message=message, legacy_alias_key=None)
        except ValidationError:
            raise
        except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
            logger.error("add_group_stock exception: %s", exc)
            raise ExternalServiceError("add_group_stock_failed", details={"reason": str(exc)}) from exc

    @blueprint.delete("/stock-groups/<int:group_id>/stocks/<symbol>")
    @login_required
    def remove_group_stock(group_id: int, symbol: str):
        symbol = symbol.strip()
        if not symbol:
            raise ValidationError("symbol_required", details={"reason": "股票代码不能为空"})
        success, message = _stock_group_svc().remove_symbol(group_id, symbol, user_id=runtime.user_id())
        if success:
            runtime.record_audit("remove_watchlist", "stock", symbol, {"group_id": group_id})
        if not success and message and "不在当前分组中" in message:
            return ok_response(message="已移除", legacy_alias_key=None, enable_legacy_alias=legacy)
        runtime.require_ok(success, message, code="stock_group_remove_symbol_failed")
        return ok_response(message=message, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.delete("/stock-groups/<int:group_id>/stocks/clear")
    @login_required
    def clear_group_stocks(group_id: int):
        success, message = _stock_group_svc().clear_group(group_id, user_id=runtime.user_id())
        runtime.require_ok(success, message, code="stock_group_clear_failed")
        return ok_response(message=message, legacy_alias_key=None)

    @blueprint.post("/stock-groups/<int:from_group_id>/move/<symbol>/to/<int:to_group_id>")
    @login_required
    def move_stock_group(from_group_id: int, symbol: str, to_group_id: int):
        uid = runtime.user_id()
        svc = _stock_group_svc()
        success_rem, msg_rem = svc.remove_symbol(from_group_id, symbol, user_id=uid)
        if not success_rem:
            raise ValidationError(
                "watchlist_move_remove_failed",
                details={"reason": f"从原分组移除失败: {msg_rem}"},
            )

        success_add, msg_add = svc.add_symbol(to_group_id, symbol, user_id=uid)
        if not success_add:
            svc.add_symbol(from_group_id, symbol, user_id=uid)
            raise ValidationError(
                "watchlist_move_add_failed",
                details={"reason": f"添加到新分组失败: {msg_add}"},
            )

        runtime.record_audit("move_watchlist", "stock", symbol, {"from": from_group_id, "to": to_group_id})
        return ok_response(data={"ok": True, "message": "移动成功"})
