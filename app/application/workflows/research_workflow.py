from __future__ import annotations

"""Research workflow — AI analysis, factor mining, report generation."""


from typing import Any

from app.application.workflows.base_workflow import BaseWorkflow
from app.core.event_bus import emit_workflow_completed
from app.domain.agent_workflow import WorkflowContext
from app.domain.enums import MarketCode
from app.modules.user.services.user.user_knowledge_service import UserKnowledgeService


def _CapabilityRegistry():
    """Lazy import via factory to avoid app->infra module-level dependency."""
    from app.infrastructure.capabilities.registry import CapabilityRegistry as _CR
    return _CR()


class ResearchWorkflow(BaseWorkflow):
    """End-to-end research workflow: data → AI analysis → report."""

    workflow_type = "research"

    def __init__(
        self,
        workflow_id: str,
        symbol: str,
        market: MarketCode,
        capability_registry: CapabilityRegistry | None = None,
        user_id: str | int | None = None,
        knowledge_service: UserKnowledgeService | None = None,
        **kwargs: Any,
    ) -> None:
        self._symbol = symbol
        self._market = market
        self._user_id = user_id
        self._knowledge = knowledge_service
        super().__init__(workflow_id=workflow_id, name=f"Research {symbol}", capability_registry=capability_registry, **kwargs)

    def _build_steps(self) -> None:
        self._workflow.add_step("gather_data", self._step_gather_data, required=True, timeout=120)
        self._workflow.add_step("ai_analysis", self._step_ai_analysis, required=True, timeout=300)
        self._workflow.add_step("generate_report", self._step_generate_report, required=False, timeout=60)

    def _step_gather_data(self, ctx: WorkflowContext) -> dict[str, Any]:
        user_ctx = {}
        if self._user_id is not None and self._knowledge is not None:
            user_ctx = self._knowledge.get_workflow_context(self._user_id)

        bars, bar_note = self._capabilities.execute("fetch_bars", symbol=self._symbol, market=self._market, period="1y")
        profile, prof_note = self._capabilities.execute("fetch_profile", symbol=self._symbol, market=self._market)
        bundle = self._capabilities.execute("cn_financial_bundle", symbol=self._symbol)[0] if self._market == MarketCode.CN else {}
        return {
            "symbol": self._symbol,
            "market": self._market.value,
            "bar_count": len(bars or []),
            "bars_note": bar_note,
            "has_profile": profile is not None,
            "has_financials": bool(bundle),
            "user_context": user_ctx,
        }

    def _step_ai_analysis(self, ctx: WorkflowContext) -> dict[str, Any]:
        data = ctx.data.get("gather_data", {})
        return {
            "symbol": self._symbol,
            "analysis": f"AI analysis placeholder for {self._symbol}",
            "data_summary": data,
        }

    def _step_generate_report(self, ctx: WorkflowContext) -> dict[str, Any]:
        analysis = ctx.data.get("ai_analysis", {})
        return {
            "report": f"Research report for {self._symbol}",
            "sections": ["overview", "analysis", "recommendation"],
            "source": analysis,
        }

    def on_completed(self, final_result: dict[str, Any]) -> None:
        emit_workflow_completed(
            workflow_id=self._workflow_id,
            workflow_type=self.workflow_type,
            state="completed",
            evidence_count=len(final_result),
            step_metrics=getattr(self, '_latest_optimizer_metrics', None),
        )
        if self._user_id is not None and self._knowledge is not None:
            self._knowledge.record_decision(
                self._user_id,
                symbol=self._symbol,
                action="research",
                workflow_id=self._workflow_id,
                detail={"summary": final_result.get("generate_report", {})},
            )
