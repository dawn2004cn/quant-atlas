from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Blueprint, Response, request
from flask_login import login_required

from app.presentation.api.common import ok_response


def register_investment_manager_user_routes(
    blueprint: Blueprint,
    *,
    legacy: bool,
    svc: Callable[[], Any],
) -> None:
    @blueprint.post("/investment-managers/user/set-cash")
    @login_required
    def user_set_cash():
        body = request.get_json(silent=True) or {}
        account_id = (body.get("account_id") or "USER").strip()
        name = (body.get("name") or "我的账户").strip()
        cash = float(body.get("cash") or 0)
        out = svc().user_set_cash(account_id=account_id, name=name, cash=cash)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/investment-managers/user/import-trades")
    @login_required
    def user_import_trades():
        body = request.get_json(silent=True) or {}
        account_id = (body.get("account_id") or "USER").strip()
        name = (body.get("name") or "我的账户").strip()
        cash = float(body.get("cash") or 10_000_000)
        trades = body.get("trades") or []
        out = svc().user_import_trades(account_id=account_id, name=name, cash=cash, trades=trades)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/investment-managers/user/<account_id>/trades.csv")
    @login_required
    def export_user_trades(account_id: str):
        filename, data = svc().export_user_trades_csv(account_id)
        return Response(
            data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
