"""Retail assistant picks and meta-learning routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.presentation.api.common import ok_response, parse_market
from app.presentation.api.request_parsers import parse_float_param, parse_int_param
from app.presentation.api.v1.retail_assistant.runtime import RetailAssistantRuntime
from app.presentation.api.v1_context import ApiV1Context

from ...decorators import service_fallback


def register_retail_assistant_insight_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: RetailAssistantRuntime,
) -> None:
    legacy = runtime.legacy

    @blueprint.get("/retail-assistant/daily-top-picks")
    @login_required
    @service_fallback("recommendation_service")
    def retail_assistant_daily_top_picks():
        """早盘 Top-N 推荐（产业链位置 + 买卖区间 + 胜率估算）。"""
        rec = getattr(ctx, "recommendation_service", None)
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
        user_id = int(getattr(current_user, "id", None) or 0) or None
        return ok_response(
            data=rec.daily_top(
                market=market,
                top_n=top_n,
                account_equity=account_equity,
                user_id=user_id,
            ),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/retail-assistant/meta-learning-status")
    @login_required
    def retail_assistant_meta_learning_status():
        """AutoValidator 排名与 Top3 调权说明（元学习闭环摘要）。"""
        from app.modules.user.services.user.retail_meta_learning_service import (
            retail_meta_learning_status,
        )

        return ok_response(
            data=retail_meta_learning_status(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
