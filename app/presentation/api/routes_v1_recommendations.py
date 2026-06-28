from __future__ import annotations

"""Recommendation API routes."""


from flask import request
from flask_login import login_required

from app.core.registry import register_routes

from .common import ok_response, parse_market
from .request_parsers import parse_float_param, parse_int_param
from .route_deps import RecommendationRouteDeps
from .v1_context import ApiV1Context


@register_routes(name="recommendation", context="strategy", description="Daily stock recommendations")
def register_recommendation_routes(
    blueprint,
    ctx: ApiV1Context,
    *,
    deps: RecommendationRouteDeps | None = None,
) -> None:
    legacy = (
        deps.enable_legacy_response_fields
        if deps is not None
        else bool(ctx.enable_legacy_response_fields)
    )
    bound_service = deps.recommendation_service if deps is not None else ctx.recommendation_service

    @blueprint.get("/recommendations/daily")
    @login_required
    def daily_recommendations():

        service = bound_service or getattr(ctx, "recommendation_service", None)
        if service is None:
            return ok_response(
                data={"message": "recommendation_service not available"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        market = parse_market(request.args.get("market", "CN"))
        top_n = min(
            parse_int_param(request.args.get("top_n"), name="top_n", default=3, min_value=1),
            5,
        )
        account_equity = parse_float_param(
            request.args.get("account_equity"),
            name="account_equity",
            default=100000.0,
            min_value=1000.0,
        )
        return ok_response(
            data=service.daily_top(
                market=market,
                top_n=top_n,
                account_equity=account_equity,
            ),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
