"""Trade plan build and adopt routes."""

from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response, parse_market
from app.presentation.api.request_parsers import parse_float_param
from app.presentation.api.v1.trade_plan.runtime import TradePlanRuntime
from app.presentation.api.v1_context import ApiV1Context

from ...decorators import service_fallback


def register_trade_plan_core_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TradePlanRuntime,
) -> None:
    _ = ctx

    @blueprint.get("/trade-plan")
    @login_required
    @service_fallback("trade_plan_service")
    def trade_plan():
        svc = getattr(ctx, "trade_plan_service", None)
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        m = parse_market(request.args.get("market", "CN"))
        from app.modules.system.services.ui.attribution_timeline_service import AttributionTimelineService
        timeline = AttributionTimelineService(
            stock_service=getattr(runtime.ctx, "stock_service", None),
            news_archive=getattr(runtime.ctx, "news_archive", None),
            fundamental_access=getattr(runtime.ctx, "fundamental_access", None),
            basic_market_data_service=getattr(runtime.ctx, "basic_market_data_service", None),
        ).build_timeline(
            symbol,
            m,
            start=(datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
            end=datetime.now().strftime("%Y-%m-%d"),
            limit=15,
        )
        entry_raw = request.args.get("entry_price")
        entry_price = None
        if entry_raw not in (None, ""):
            entry_price = parse_float_param(entry_raw, name="entry_price", default=0.0)
        payload = svc.build_plan(
            timeline=timeline,
            symbol=symbol,
            market=parse_market(request.args.get("market", "CN")),
            account_equity=parse_float_param(
                request.args.get("account_equity"),
                name="account_equity",
                default=100000.0,
            ),
            cash_available=parse_float_param(
                request.args.get("cash_available"),
                name="cash_available",
                default=100000.0,
            ),
            risk_per_trade_pct=parse_float_param(
                request.args.get("risk_per_trade_pct"),
                name="risk_per_trade_pct",
                default=1.0,
            ),
            max_position_pct=parse_float_param(
                request.args.get("max_position_pct"),
                name="max_position_pct",
                default=15.0,
            ),
            entry_price=entry_price,
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=runtime.ctx.enable_legacy_response_fields,
        )

    def _execute_adopt():
        body = request.get_json(silent=True) or {}
        symbol = str(body.get("symbol") or request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        market = parse_market(str(body.get("market") or request.args.get("market") or "CN"))
        source = str(body.get("source") or "trade_plan_adopt").strip() or "trade_plan_adopt"
        strategy_id = str(body.get("strategy_id") or body.get("strategy") or "").strip() or None
        entry_raw = body.get("entry_price")
        entry_price = None
        if entry_raw not in (None, ""):
            entry_price = parse_float_param(entry_raw, name="entry_price", default=0.0)

        svc = runtime.adoption_service()
        try:
            return svc.adopt(
                user_id=runtime.user_id(),
                symbol=symbol,
                market=market,
                source=source,
                strategy_id=strategy_id,
                account_equity=parse_float_param(
                    body.get("account_equity"),
                    name="account_equity",
                    default=100000.0,
                ),
                cash_available=parse_float_param(
                    body.get("cash_available"),
                    name="cash_available",
                    default=100000.0,
                ),
                risk_per_trade_pct=parse_float_param(
                    body.get("risk_per_trade_pct"),
                    name="risk_per_trade_pct",
                    default=1.0,
                ),
                max_position_pct=parse_float_param(
                    body.get("max_position_pct"),
                    name="max_position_pct",
                    default=15.0,
                ),
                entry_price=entry_price,
                reason=str(body.get("reason") or "").strip(),
                ai_summary=str(body.get("ai_summary") or body.get("note") or "").strip(),
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    @blueprint.post("/trade-plan/adopt")
    @login_required
    def trade_plan_adopt():
        """Build plan and persist as an open signal observation (one-click adopt)."""
        payload = _execute_adopt()
        runtime.after_adopt_hooks(payload)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=runtime.ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/trade-plans/adopt")
    @login_required
    def trade_plans_adopt_alias():
        """REST alias for ``POST /trade-plan/adopt``."""
        payload = _execute_adopt()
        runtime.after_adopt_hooks(payload)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=runtime.ctx.enable_legacy_response_fields,
        )
