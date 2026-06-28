from __future__ import annotations

"""API v1：自选股智能体。"""


from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from .common import ok_response, parse_market
from .request_parsers import parse_bool_param, parse_int_param
from .v1_context import ApiV1Context


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes
def register_watchlist_agent_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register watchlist agent endpoints."""

    @blueprint.get("/watchlist/agent")
    @login_required
    def watchlist_agent_snapshot():
        svc = getattr(ctx, "watchlist_agent_service", None)
        if svc is None:
            raise ValidationError("watchlist_agent_service_unavailable")
        raw_group = (request.args.get("group_id") or "").strip()
        group_id = None
        if raw_group:
            group_id = parse_int_param(raw_group, name="group_id", min_value=1)
        limit = parse_int_param(request.args.get("limit"), name="limit", default=50, min_value=1)
        include_news = parse_bool_param(
            request.args.get("include_news"),
            name="include_news",
            default=False,
        )
        payload = svc.build_snapshot(
            user_id=_uid(),
            market=parse_market(request.args.get("market", "CN")),
            group_id=group_id,
            limit=min(limit, 100),
            include_news=include_news,
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )
