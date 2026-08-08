from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from flask import Blueprint, Response
from flask_login import login_required

from app.application.errors import NotFoundError
from app.core.logger import get_logger
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_int_param

logger = get_logger(__name__)


def register_investment_manager_crud_routes(
    blueprint: Blueprint,
    *,
    legacy: bool,
    svc: Callable[[], Any],
    uid: Callable[[], int],
) -> None:
    @blueprint.post("/investment-managers/seed")
    @login_required
    def seed_managers():
        out = svc().ensure_seed_managers()
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/investment-managers/deploy")
    @login_required
    def deploy_batch():
        from flask import request

        body = request.get_json(silent=True) or {}
        bs = parse_int_param(body.get("batch_size"), name="batch_size", default=10, min_value=1)
        bs = min(bs, 30)
        out = svc().deploy_next_batch(batch_size=bs)
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/investment-managers")
    @login_required
    def list_managers():
        items = svc().list_managers()
        return ok_response(
            data={"items": items, "count": len(items)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/investment-managers/leaderboard")
    @login_required
    def leaderboard():
        from flask import request

        period = (request.args.get("period") or "day").strip().lower()
        items = svc().leaderboard(period=period)

        total_trades = 0
        managers_with_trades = 0
        try:
            stats = svc().trade_stats_by_manager()
            stat_rows = stats.values() if isinstance(stats, dict) else stats
            total_trades = sum(
                (s.get("trade_count", 0) if isinstance(s, dict) else int(s[1])) for s in stat_rows
            )
            managers_with_trades = len(
                [
                    s
                    for s in stat_rows
                    if (s.get("trade_count", 0) if isinstance(s, dict) else int(s[1])) > 0
                ]
            )
        except Exception as exc:
            logger.warning("leaderboard trade_stats aggregate failed: %s", exc)

        return ok_response(
            data={
                "items": items,
                "count": len(items),
                "aggregate": {
                    "total_trades": total_trades,
                    "managers_with_trades": managers_with_trades,
                },
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/investment-managers/me")
    @login_required
    def my_manager():
        try:
            items = svc().list_managers()
            for m in items:
                if str(m.get("user_id")) == str(uid()):
                    return ok_response(data=m, legacy_alias_key=None, enable_legacy_alias=legacy)
        except Exception as exc:
            logger.warning("my_manager list_managers failed: %s", exc)
        return ok_response(
            data={"id": "me", "name": "My Manager", "user_id": str(uid())},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/investment-managers/<manager_id>")
    @login_required
    def manager_detail(manager_id: str):
        from flask import request

        d = (request.args.get("date") or "").strip()[:10] or datetime.now().strftime("%Y-%m-%d")
        out = svc().manager_detail(manager_id, date=d)
        if out is None:
            raise NotFoundError(
                "investment_manager_not_found",
                details={"manager_id": manager_id},
            )
        return ok_response(data=out, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/investment-managers/<manager_id>/trades.csv")
    @login_required
    def export_manager_trades(manager_id: str):
        filename, data = svc().export_manager_trades_csv(manager_id)
        return Response(
            data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
