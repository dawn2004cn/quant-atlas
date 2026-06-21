from __future__ import annotations
"""API v1: AI Agent routes - RAG and Investment Committee."""


from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.registry import register_routes
from .common import ok_resource, require_ctx_service
from .v1_context import ApiV1Context
from .request_parsers import parse_int_param
from .decorators import service_fallback


@register_routes(name="ai_agent", context="ai_agent", description="AI Agent routes - RAG and Investment Committee")
def register_ai_agent_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    @blueprint.get("/ai/rag/reports")
    @login_required
    @service_fallback("research_report_rag_service")
    def ai_rag_search_reports():
        """Search research reports using semantic query."""
        rag = getattr(ctx, "research_report_rag_service", None)

        symbol = request.args.get("symbol", "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")

        query = request.args.get("query", "").strip()
        if not query:
            query = "analysis recommendation"

        market = request.args.get("market", "CN")
        limit = parse_int_param(request.args.get("limit"), name="limit", default=10)

        reports = rag.search_reports(
            symbol=symbol,
            query=query,
            market=market,
            limit=limit,
        )

        return ok_resource(
            resource={"reports": reports},
            resource_key="rag_reports",
            enable_legacy_alias=False,
        )

    @blueprint.get("/ai/rag/trend")
    @login_required
    @service_fallback("research_report_rag_service")
    def ai_rag_opinion_trend():
        """Get opinion trend for a symbol."""
        rag = getattr(ctx, "research_report_rag_service", None)

        symbol = request.args.get("symbol", "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")

        market = request.args.get("market", "CN")
        limit = parse_int_param(request.args.get("limit"), name="limit", default=20)

        trend = rag.summarize_opinion_trend(
            symbol=symbol,
            market=market,
            limit=limit,
        )

        return ok_resource(
            resource=trend,
            resource_key="opinion_trend",
            enable_legacy_alias=False,
        )

    @blueprint.get("/ai/committee/evaluate")
    @login_required
    @service_fallback("investment_committee_service")
    def ai_committee_evaluate():
        """Run Investment Committee evaluation for a stock."""
        committee = getattr(ctx, "investment_committee_service", None)

        symbol = request.args.get("symbol", "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")

        market = request.args.get("market", "CN")

        decision = committee.evaluate_stock(
            symbol=symbol,
            market=market,
        )

        return ok_resource(
            resource={
                "symbol": decision.symbol,
                "final_verdict": decision.final_verdict,
                "confidence": decision.confidence,
                "consensus_score": decision.consensus_score,
                "summary": decision.summary,
                "agent_opinions": [
                    {
                        "agent_name": op.agent_name,
                        "conclusion": op.conclusion,
                        "confidence": op.confidence,
                        "reasoning": op.reasoning,
                    }
                    for op in decision.agent_opinions
                ],
            },
            resource_key="committee_decision",
            enable_legacy_alias=False,
        )
