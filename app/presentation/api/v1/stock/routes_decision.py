from __future__ import annotations

"""Stock decision brief route."""

from flask import Blueprint, request
from flask_login import login_required

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.modules.system.services.ui.data_freshness_service import enrich_market_payload

from ...common import ok_response, parse_market
from ...decorators import service_fallback
from ...request_parsers import parse_int_param
from ...stock_route_helpers import build_sector_context

logger = get_logger(__name__)


@register_routes(name="stock_decision", context="market_data", description="Stock decision brief")
def register_stock_decision(blueprint: Blueprint, ctx) -> None:

    legacy = ctx.enable_legacy_response_fields
    stock_service = ctx.stock_service

    @blueprint.get("/stocks/<market>/<symbol>/decision-brief")
    @login_required
    @service_fallback("stock_service")
    def stock_decision_brief(market: str, symbol: str):

        from flask_login import current_user

        from app.domain.shared.market_fact import enrich_quote_with_facts
        from app.modules.market_data.services.data_coverage_service import DataCoverageService
        from app.modules.system.services.ui.attribution_timeline_service import (
            AttributionTimelineService,
        )
        from app.modules.system.services.ui.decision_brief_service import DecisionBriefService
        from app.modules.system.services.ui.user_decision_context_service import (
            UserDecisionContextService,
        )

        m = parse_market(market)

        limit = parse_int_param(
            request.args.get("timeline_limit"),
            name="timeline_limit",
            default=30,
            min_value=1,
            max_value=120,
        )

        detail_raw = stock_service.get_stock_detail(symbol, m)

        detail = detail_raw if isinstance(detail_raw, dict) else (detail_raw.to_dict() if hasattr(detail_raw, "to_dict") else detail_raw)

        profile = detail.get("profile", {}) or {}

        realtime = profile.get("realtime", {}) if isinstance(profile, dict) else {}

        detail["quote_fact"] = enrich_quote_with_facts(
            realtime,
            detail.get("indicators") or {},
            symbol=symbol,
            market=m.value,
        )

        detail["data_coverage"] = DataCoverageService(stock_service).assess_symbol(
            symbol,
            m,
        ).model_dump()

        detail["_quote_freshness"] = enrich_market_payload(
            {
                **realtime,
                "symbol": symbol,
                "market": m.value,
                "quote_time": realtime.get("quote_time") or realtime.get("updated_at"),
            },
            source="stock_detail",
        )

        sector_ctx = build_sector_context(
            symbol=symbol,
            market=m,
            industry_chain_service=ctx.industry_chain_service,
        )

        timeline = AttributionTimelineService(
            stock_service=stock_service,
            news_archive=ctx.news_archive,
            fundamental_access=ctx.fundamental_access,
            basic_market_data_service=ctx.basic_market_data_service,
        ).build_timeline(
            symbol,
            m,
            start=request.args.get("start"),
            end=request.args.get("end"),
            limit=limit,
        )

        user_id = getattr(current_user, "id", "anonymous")

        profile_pref = {}

        page_pref = {}

        if ctx.user_investment_profile_service is not None:

            profile_pref = ctx.user_investment_profile_service.get_profile(user_id)

        if ctx.page_preference_service is not None:

            page_pref = ctx.page_preference_service.get_preferences(user_id)

        decision_ctx_service = getattr(ctx, "user_decision_context_service", None)
        if decision_ctx_service is None or isinstance(decision_ctx_service, type):
            decision_ctx_service = UserDecisionContextService()

        decision_context = decision_ctx_service.build_context(
            user_id=user_id,
            role=request.args.get("role"),
            investment_profile=profile_pref,
            page_preferences=page_pref,
            page="stock_detail",
        )

        history_for_evidence: list[dict] = []

        market_svc = getattr(ctx, "market_service", None)

        if market_svc is None and getattr(ctx, "market", None) is not None:

            market_svc = getattr(ctx.market, "market_service", None)

        if market_svc is not None:

            try:

                from datetime import datetime, timedelta

                end = datetime.now()

                start = end - timedelta(days=280)

                hist_dto = market_svc.get_history(
                    symbol,
                    m,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                )

                raw_hist = getattr(hist_dto, "history", hist_dto) or []

                history_for_evidence = [
                    h.__dict__ if hasattr(h, "__dict__") else dict(h) if isinstance(h, dict) else {}
                    for h in raw_hist
                ]

            except Exception:

                history_for_evidence = []

        from app.modules.system.services.ui.evidence_traceability_service import (
            EvidenceTraceabilityService,
        )

        realtime = profile.get("realtime", {}) if isinstance(profile, dict) else {}

        yanbao_items: list[dict] = []

        bmd = getattr(ctx, "basic_market_data_service", None)

        if bmd is not None:

            try:

                yanbao_items = list(bmd.yanbao_list(limit=300) or [])

            except Exception:

                yanbao_items = []

        supporting = EvidenceTraceabilityService().build_supporting_evidence(
            symbol=symbol,
            market=m.value,
            quote=realtime if isinstance(realtime, dict) else {},
            history=history_for_evidence,
            indicators=detail.get("indicators") or {},
            yanbao_items=yanbao_items,
        )

        payload = DecisionBriefService().build_brief(
            symbol=symbol,
            market=m.value,
            stock_detail=detail,
            timeline=timeline,
            decision_context=decision_context,
            sector_context=sector_ctx,
            supporting_evidence=supporting,
        )

        payload["decision_context"] = decision_context

        payload["sector_context"] = sector_ctx

        try:

            if decision_ctx_service is not None:

                decision_ctx_service.record_event(
                    user_id=user_id,
                    event_type="decision_brief_view",
                    symbol=symbol,
                    market=m.value,
                    page="stock_detail",
                    component="decision_brief",
                    action="view",
                    detail={"role": decision_context.get("role"), "component_count": len(payload.get("components", []))},
                )

        except Exception as _exc:

            logger.warning("stock payload audit skipped: %s", _exc)

        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            count=len(payload["components"]),
        )
