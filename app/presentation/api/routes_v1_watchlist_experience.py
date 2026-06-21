from __future__ import annotations
"""Watchlist deep experience API routes."""


from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from .common import ok_response, parse_market, ensure_service
from .request_parsers import parse_optional_bool_param
from .v1_context import ApiV1Context
from app.core.registry import register_routes


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes
def register_watchlist_experience_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    @blueprint.get("/watchlist/experience")
    @login_required
    def watchlist_experience():
        svc = ensure_service(ctx, "watchlist_experience_service")
        group_raw = request.args.get("group_id")
        group_id = int(group_raw) if group_raw not in (None, "") else None
        include_news = parse_optional_bool_param(request.args.get("include_news"), name="include_news")
        payload = svc.dashboard(
            user_id=_uid(),
            market=parse_market(request.args.get("market", "CN")),
            group_id=group_id,
            sort_by=request.args.get("sort_by", "priority"),
            include_news=bool(include_news),
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )
