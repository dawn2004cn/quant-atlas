from __future__ import annotations

"""API v1：今日操盘台聚合快照。"""


from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes

from ...core.middleware.request_context import require_authenticated_user_id
from .common import ok_response, parse_market
from .request_parsers import parse_int_param
from .route_deps import (
    WorkbenchRouteDeps,
    build_workbench_route_deps,
    require_daily_workbench_service,
)
from .v1_context import ApiV1Context


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="daily_workbench", context="misc", description="今日操盘台聚合快照")
def register_daily_workbench_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
    *,
    deps: WorkbenchRouteDeps | None = None,
) -> None:
    """Register daily workbench endpoints."""
    route_deps = deps or build_workbench_route_deps(ctx)

    @blueprint.get("/daily-workbench")
    @login_required
    def daily_workbench_snapshot():
        svc = require_daily_workbench_service(route_deps)

        watchlist_limit = parse_int_param(
            request.args.get("watchlist_limit"),
            name="watchlist_limit",
            default=12,
            min_value=1,
        )
        signal_limit = parse_int_param(
            request.args.get("signal_limit"),
            name="signal_limit",
            default=12,
            min_value=1,
        )
        focus_symbol = (request.args.get("symbol") or "").strip() or None
        payload = svc.build_snapshot(
            _uid(),
            market=parse_market(request.args.get("market", "CN")),
            watchlist_limit=min(watchlist_limit, 50),
            signal_limit=min(signal_limit, 50),
            focus_symbol=focus_symbol,
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=route_deps.enable_legacy_response_fields,
        )
