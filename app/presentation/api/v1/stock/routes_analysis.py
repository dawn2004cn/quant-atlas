from __future__ import annotations

"""Stock live document and analysis routes."""

from flask import Blueprint, request
from flask_login import login_required

from app.core.registry import register_routes

from ...common import ok_response, parse_market
from ...decorators import service_fallback


@register_routes(name="stock_live_analysis", context="market_data", description="Stock live document & analysis")
def register_stock_live_analysis(blueprint: Blueprint, ctx) -> None:

    legacy = ctx.enable_legacy_response_fields
    stock_service = ctx.stock_service
    analysis_service = ctx.analysis_service
    @login_required
    def stock_live_document(market: str, symbol: str):

        """Live-Document unified streaming research payload."""

        from app.modules.system.services.ui.live_research_document_service import (
            LiveResearchDocumentService,
        )

        m = parse_market(market)

        full = (request.args.get("full") or "").strip().lower() in {"1", "true", "yes"}

        svc = LiveResearchDocumentService()

        doc = svc.build_document(
            symbol,
            m,
            stock_service=ctx.stock_service,
            strategy_copilot_service=getattr(ctx, "strategy_copilot_service", None),
            sequence_chain_service=getattr(ctx, "sequence_chain_service", None),
            include_handover=full,
        )

        doc = svc.apply_lights_from_payload(doc)

        return ok_response(data=doc, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/stocks/<market>/<symbol>/analysis")
    @service_fallback("stock_service")
    @service_fallback("analysis_service")
    @login_required
    def stock_analysis(market: str, symbol: str):
        m = parse_market(market)

        detail = stock_service.get_stock_detail(symbol, m)

        user_hypothesis = (request.args.get("user_hypothesis") or "").strip() or None

        hypothesis_id = (request.args.get("hypothesis_id") or "").strip() or None

        payload = analysis_service.build_analysis(
            symbol,
            detail,
            user_hypothesis=user_hypothesis,
            hypothesis_id=hypothesis_id,
        )

        from app.modules.market_data.services.data_coverage_service import DataCoverageService

        payload["data_coverage"] = DataCoverageService(stock_service).assess_symbol(
            symbol, m
        ).model_dump()

        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
