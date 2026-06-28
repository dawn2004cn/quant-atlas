from __future__ import annotations

"""Workflow service — registry & lifecycle management for all workflow types."""


from typing import Any

from app.application.workflows.base_workflow import BaseWorkflow
from app.application.workflows.data_pipeline_workflow import DataPipelineWorkflow
from app.application.workflows.healing import CircuitBreaker
from app.application.workflows.optimizer import WorkflowOptimizer
from app.application.workflows.research_workflow import ResearchWorkflow
from app.application.workflows.trading_workflow import TradingWorkflow
from app.domain.enums import MarketCode
from app.infrastructure.capabilities.registry import CapabilityRegistry


class WorkflowService:
    """Application service that creates, tracks, and manages workflow instances.

    Provides a single entry point for web routes and Celery tasks to interact
    with any workflow type.  Integrates auto-healing and adaptive timeouts.
    """

    def __init__(
        self,
        capability_registry: CapabilityRegistry | None = None,
        optimizer: WorkflowOptimizer | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._capabilities = capability_registry or CapabilityRegistry()
        self._optimizer = optimizer or WorkflowOptimizer()
        self._circuit_breaker = circuit_breaker
        self._workflows: dict[str, BaseWorkflow] = {}

    # ── factory ──────────────────────────────────────────────────────────

    def _build_base_kwargs(self) -> dict[str, Any]:
        return {
            "capability_registry": self._capabilities,
            "optimizer": self._optimizer,
            "circuit_breaker": self._circuit_breaker,
        }

    def create_research(
        self,
        workflow_id: str,
        symbol: str,
        market: MarketCode,
    ) -> ResearchWorkflow:
        wf = ResearchWorkflow(
            workflow_id=workflow_id,
            symbol=symbol,
            market=market,
            **self._build_base_kwargs(),
        )
        self._workflows[workflow_id] = wf
        return wf

    def create_trading(
        self,
        workflow_id: str,
        symbol: str,
        market: MarketCode,
        strategy_name: str = "",
    ) -> TradingWorkflow:
        wf = TradingWorkflow(
            workflow_id=workflow_id,
            symbol=symbol,
            market=market,
            strategy_name=strategy_name,
            **self._build_base_kwargs(),
        )
        self._workflows[workflow_id] = wf
        return wf

    def create_data_pipeline(
        self,
        workflow_id: str,
        pipeline_name: str,
        symbols: list[str] | None = None,
    ) -> DataPipelineWorkflow:
        wf = DataPipelineWorkflow(
            workflow_id=workflow_id,
            pipeline_name=pipeline_name,
            symbols=symbols,
            **self._build_base_kwargs(),
        )
        self._workflows[workflow_id] = wf
        return wf

    # ── lifecycle ────────────────────────────────────────────────────────

    def get(self, workflow_id: str) -> BaseWorkflow | None:
        return self._workflows.get(workflow_id)

    def start(self, workflow_id: str, initial_data: dict[str, Any] | None = None) -> str | None:
        wf = self.get(workflow_id)
        if wf is None:
            return None
        return wf.start(initial_data=initial_data)

    def pause(self, workflow_id: str) -> bool:
        wf = self.get(workflow_id)
        if wf is None:
            return False
        wf.pause()
        return True

    def cancel(self, workflow_id: str) -> bool:
        wf = self.get(workflow_id)
        if wf is None:
            return False
        wf.cancel()
        return True

    def resume(self, workflow_id: str, approved: bool, feedback: str | None = None) -> dict[str, Any] | None:
        wf = self.get(workflow_id)
        if wf is None:
            return None
        return wf.resume(approved=approved, feedback=feedback)

    def request_human_intervention(self, workflow_id: str, message: str) -> bool:
        wf = self.get(workflow_id)
        if wf is None:
            return False
        wf.request_human_intervention(message)
        return True

    # ── query ────────────────────────────────────────────────────────────

    def get_status(self, workflow_id: str) -> dict[str, Any] | None:
        wf = self.get(workflow_id)
        if wf is None:
            return None
        return wf.get_status()

    def get_evidence(self, workflow_id: str) -> list[dict[str, Any]] | None:
        wf = self.get(workflow_id)
        if wf is None:
            return None
        return wf.get_evidence()

    def get_optimizer_summary(self) -> dict[str, Any]:
        return self._optimizer.summary()

    def list_workflows(self) -> list[dict[str, Any]]:
        return [
            {
                "workflow_id": wid,
                "name": wf._workflow.name,
                "workflow_type": wf.workflow_type,
                "state": wf._workflow.state.value,
            }
            for wid, wf in self._workflows.items()
        ]
