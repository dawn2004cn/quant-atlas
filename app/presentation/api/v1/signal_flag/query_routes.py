"""Signal-flag pool query routes."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.signal_flag.runtime import SignalFlagRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_signal_flag_query_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: SignalFlagRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/signal-flag/dates")
    @login_required
    def signal_flag_dates():
        limit = parse_int_param(request.args.get("limit"), name="limit", default=120, min_value=1)
        limit = min(limit, 400)
        dates = runtime.require_service().list_dates(limit=limit)
        return ok_response(
            data={"dates": dates},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/signal-flag/pool")
    @login_required
    def signal_flag_pool():
        raw = (request.args.get("date") or "").strip()[:10]
        pool_date = raw or datetime.now().strftime("%Y-%m-%d")
        items = runtime.require_service().get_pool(pool_date)
        return ok_response(
            data={"pool_date": pool_date, "count": len(items), "items": items},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
