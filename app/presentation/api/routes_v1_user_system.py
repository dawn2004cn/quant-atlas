"""API v1: User knowledge and workflow hub."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from ...domain.enums import MarketCode
from .common import ok_response
from .decorators import require_role
from .v1_context import ApiV1Context


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="user_knowledge", context="system", description="User knowledge and workflow hub")
def register_user_knowledge_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register user knowledge and workflow hub routes."""
    legacy = ctx.enable_legacy_response_fields
    task_message_store = ctx.task_message_store

    @blueprint.get("/user/knowledge")
    @login_required
    def user_knowledge_get():
        """Persistent preference/decision knowledge used to enrich AgentContext."""
        svc = getattr(ctx, "user_knowledge_service", None)
        if svc is None:
            return ok_response(
                data={"message": "user_knowledge_service not available"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        symbol = (request.args.get("symbol") or "").strip()
        sector = (request.args.get("sector") or "").strip()
        user_id = _uid()
        return ok_response(
            data={
                "profile": svc.get_profile(user_id),
                "context_enrichment": svc.build_context_enrichment(
                    user_id,
                    symbol=symbol,
                    sector=sector,
                ),
                "behavior_topology": svc.analyze_topology(user_id),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/user/knowledge/topology")
    @login_required
    def user_knowledge_topology():
        """Behavior topology: fatigue, cognitive bias alerts."""
        svc = getattr(ctx, "user_knowledge_service", None)
        if svc is None:
            return ok_response(
                data={"message": "user_knowledge_service not available"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        user_id = _uid()
        return ok_response(
            data=svc.analyze_topology(user_id),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/user/knowledge")
    @login_required
    @require_role("can_manage_users")
    def user_knowledge_record():
        """Record user attention and decision outcomes for personalization."""
        svc = getattr(ctx, "user_knowledge_service", None)
        if svc is None:
            return ok_response(
                data={"message": "user_knowledge_service not available"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        body = request.get_json(silent=True) or {}
        profile = svc.record_interaction(
            _uid(),
            symbols=body.get("symbols") if isinstance(body.get("symbols"), list) else [],
            sectors=body.get("sectors") if isinstance(body.get("sectors"), list) else [],
            factors=body.get("factors") if isinstance(body.get("factors"), list) else [],
            outcome=str(body.get("outcome") or "") or None,
            evidence_refs=body.get("evidence_refs") if isinstance(body.get("evidence_refs"), list) else [],
            action=str(body.get("action") or "") or None,
            stance=str(body.get("stance") or "") or None,
            page=str(body.get("page") or "") or None,
        )
        return ok_response(
            data=profile,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/workflow-hub")
    @login_required
    def workflow_hub():
        """Unified workflow hub contract for discovery, research, and execution."""
        from app.modules.system.services.ui.workflow_hub_service import WorkflowHubService

        limit_raw = request.args.get("active_limit")
        try:
            active_limit = min(max(int(limit_raw), 1), 50) if limit_raw else 20
        except ValueError:
            active_limit = 20
        payload = WorkflowHubService().build_hub(ctx, active_limit=active_limit)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/debug/market")
    @login_required
    def debug_market():
        """Debug: bypass logic to see database stats (authenticated only)."""
        market_svc = getattr(ctx, "market_service", None)
        if market_svc is None:
            return ok_response(data={"message": "market_service not available"})
        stats = market_svc.get_panorama(MarketCode.CN)
        stats_dict = stats if isinstance(stats, dict) else (stats.model_dump() if hasattr(stats, 'model_dump') else {})
        return ok_response(data=stats_dict)

    @blueprint.get("/system/trace/<trace_id>")
    @login_required
    def system_trace(trace_id: str):
        """Lightweight trace query for observability page."""
        from app.modules.system.services.monitoring.trace_query_service import TraceQueryService

        tid = (trace_id or "").strip()
        if not tid:
            return ok_response(data={"logs": [], "trace_id": ""}, legacy_alias_key=None, enable_legacy_alias=legacy)
        svc = TraceQueryService()
        logs = svc.get_traces_by_id(tid)
        return ok_response(data={"status": "success", "trace_id": tid, "logs": logs})

    @blueprint.get("/ai-committee/analyze")
    @login_required
    @require_role("can_manage_users")
    def ai_committee_analyze():
        """AI Committee analysis endpoint."""
        symbol = request.args.get("symbol", "").strip()
        market = request.args.get("market", "CN").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")
        svc = getattr(ctx, "ai_committee_service", None)
        if svc is None:
            return ok_response(
                data={"message": "ai_committee_service not available"},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        data = svc.run_debate(symbol, market)
        if task_message_store is not None:
            trace_id = f"trace-{_uid()}"
            task_message_store.push(
                event="ai_committee_debate_completed",
                task_id="sync-",
                task_name="inline.ai_committee_debate",
                detail=f"投委会辩论完成: {market} · {symbol}",
                meta={"trace_id": trace_id, "market": market, "symbol": symbol},
            )
        return ok_response(
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            data=data,
        )

    @blueprint.get("/focus/context")
    @login_required
    def focus_context():
        """Shareable focus context + cross-page navigation links."""
        from app.modules.system.services.ui.focus_context_service import FocusContextService

        from .common import parse_market

        symbol = (request.args.get("symbol") or "").strip()
        market = parse_market(request.args.get("market", "CN"))
        dto = FocusContextService().build_context(symbol, market)
        return ok_response(
            data=dto.model_dump(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/ux/decision-flow")
    @login_required
    def ux_decision_flow():
        """Unified contract for the optimized user decision workflow."""
        from app.modules.system.services.ui.decision_flow_contract_service import (
            DecisionFlowContractService,
        )

        from .common import parse_market

        market = parse_market(request.args.get("market", "CN")).value
        symbol = (request.args.get("symbol") or "{symbol}").strip() or "{symbol}"
        payload = DecisionFlowContractService().build_contract(
            market=market,
            symbol=symbol,
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    blueprint.register_blueprint(Blueprint("_user_knowledge_dummy", __name__))
