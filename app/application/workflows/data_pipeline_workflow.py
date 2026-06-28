from __future__ import annotations

"""Data pipeline workflow — ETL, sync, backfill orchestration."""


from typing import Any

from app.application.workflows.base_workflow import BaseWorkflow
from app.domain.agent_workflow import WorkflowContext


def _CapabilityRegistry():
    """Lazy import via factory to avoid app->infra module-level dependency."""
    from app.infrastructure.capabilities.registry import CapabilityRegistry as _CR
    return _CR()


class DataPipelineWorkflow(BaseWorkflow):
    """End-to-end data pipeline workflow: fetch → transform → load.

    Steps
    -----
    1. ``fetch_source`` — pull raw data from external source (TDX, EastMoney, etc.).
    2. ``transform`` — normalize and validate.
    3. ``load`` — write to target store (MySQL, Qlib binary, etc.).
    """

    workflow_type = "data_pipeline"

    def __init__(
        self,
        workflow_id: str,
        pipeline_name: str,
        symbols: list[str] | None = None,
        capability_registry: Any | None = None,
        **kwargs: Any,
    ) -> None:
        self._symbols = symbols or []
        super().__init__(workflow_id=workflow_id, name=pipeline_name, capability_registry=capability_registry, **kwargs)

    def _build_steps(self) -> None:
        self._workflow.add_step("fetch_source", self._step_fetch_source, required=True, timeout=600)
        self._workflow.add_step("transform", self._step_transform, required=True, timeout=300)
        self._workflow.add_step("load", self._step_load, required=True, timeout=600)

    def _step_fetch_source(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {
            "symbols": self._symbols,
            "source": "external",
            "fetched_count": 0,
            "status": "pending",
        }

    def _step_transform(self, ctx: WorkflowContext) -> dict[str, Any]:
        fetch_data = ctx.data.get("fetch_source", {})
        return {
            "input_count": fetch_data.get("fetched_count", 0),
            "valid_count": 0,
            "invalid_count": 0,
        }

    def _step_load(self, ctx: WorkflowContext) -> dict[str, Any]:
        transform_data = ctx.data.get("transform", {})
        return {
            "target": "mysql",
            "loaded_count": transform_data.get("valid_count", 0),
            "status": "completed",
        }
