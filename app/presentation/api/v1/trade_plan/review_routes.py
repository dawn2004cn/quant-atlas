"""Post-trade review routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.trade_plan.runtime import TradePlanRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_trade_review_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TradePlanRuntime,
) -> None:
    _ = ctx
    legacy = runtime.ctx.enable_legacy_response_fields

    @blueprint.get("/trading/review/<trade_id>")
    @login_required
    def trading_review(trade_id: str):
        """Get post-trade review card (plan 2.4)."""
        from app.modules.execution.services.trade_outcome_review_service import get_trade_review_service

        svc = get_trade_review_service()
        review = svc.get_review(trade_id)
        if not review:
            raise ValidationError(f"review_not_found: {trade_id}")
        data = {
            "trade_id": review.trade_id,
            "symbol": review.symbol,
            "direction": review.direction,
            "entry_price": review.entry_price,
            "exit_price": review.exit_price,
            "pnl": review.pnl,
            "pnl_pct": review.pnl_pct,
            "holding_days": review.holding_days,
            "summary": review.summary,
            "key_lesson": review.key_lesson,
            "generated_at": review.generated_at,
        }
        if review.attribution:
            data["attribution"] = review.attribution.model_dump()
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/trading/reviews")
    @login_required
    def trading_reviews():
        """List recent post-trade reviews."""
        from app.modules.execution.services.trade_outcome_review_service import get_trade_review_service

        svc = get_trade_review_service()
        limit = int(request.args.get("limit", 20))
        reviews = svc.list_pending_reviews(limit=limit)
        return ok_response(
            data=[
                {
                    "trade_id": r.trade_id,
                    "symbol": r.symbol,
                    "direction": r.direction,
                    "entry_price": r.entry_price,
                    "exit_price": r.exit_price,
                    "pnl": r.pnl,
                    "pnl_pct": r.pnl_pct,
                    "holding_days": r.holding_days,
                    "summary": r.summary,
                    "key_lesson": r.key_lesson,
                    "generated_at": r.generated_at,
                }
                for r in reviews
            ],
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
