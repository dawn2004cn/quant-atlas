from __future__ import annotations
"""Review tracking API routes."""


from flask import Blueprint, request
from flask_login import login_required

from ...core.middleware.request_context import require_authenticated_user_id
from .common import ok_response
from .v1_context import ApiV1Context
from app.core.registry import register_routes
from .decorators import service_fallback


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes
def register_review_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/reviews")
    @login_required
    @service_fallback("review_tracking_service")
    def list_reviews():
        svc = getattr(ctx, "review_tracking_service", None)
        items = svc.list_all() if hasattr(svc, "list_all") else []
        return ok_response(
            data={"items": items, "count": len(items)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/reviews/daily")
    @login_required
    @service_fallback("review_tracking_service")
    def daily_review():
        svc = getattr(ctx, "review_tracking_service", None)
        return ok_response(
            data=svc.daily_review(asof=request.args.get("asof"), user_id=_uid()),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/reviews/weekly")
    @login_required
    @service_fallback("review_tracking_service")
    def weekly_review():
        svc = getattr(ctx, "review_tracking_service", None)
        return ok_response(
            data=svc.weekly_review(asof=request.args.get("asof"), user_id=_uid()),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
