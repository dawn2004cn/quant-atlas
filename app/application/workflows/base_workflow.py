from __future__ import annotations

"""Base application workflow — wraps ``AgentWorkflow`` state machine."""


from abc import ABC, abstractmethod
from typing import Any

from app.domain.agent_workflow import StepStatus, WorkflowBuilder, WorkflowState

from .healing import CircuitBreaker, RetryPolicy, with_retry
from .optimizer import WorkflowOptimizer


def _CapabilityRegistry():
    """Lazy import via factory to avoid app->infra module-level dependency."""
    from app.infrastructure.capabilities.registry import CapabilityRegistry as _CR
    return _CR()


def _TaskProgressStore():
    """Lazy import via factory to avoid app->infra module-level dependency."""
    from app.infrastructure.messaging.task_progress_store import TaskProgressStore as _TPS
    return _TPS()


class BaseWorkflow(ABC):
    """Application-layer workflow that wraps the domain ``AgentWorkflow`` state
    machine and integrates with the capability plugin registry.

    Subclasses define a ``workflow_type`` and populate steps in ``_build_steps()``.
    """

    def __init__(
        self,
        workflow_id: str,
        name: str,
        capability_registry: Any | None = None,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        optimizer: WorkflowOptimizer | None = None,
    ) -> None:
        builder = WorkflowBuilder(workflow_id=workflow_id, name=name)
        self._workflow = builder.build()
        self._capabilities = capability_registry or _CapabilityRegistry()
        self._progress_store = _TaskProgressStore()
        self._retry_policy = retry_policy or RetryPolicy()
        self._circuit_breaker = circuit_breaker
        self._optimizer = optimizer
        self._build_steps()

    # ── subclass contract ────────────────────────────────────────────────

    @property
    @abstractmethod
    def workflow_type(self) -> str:
        """Machine-readable type discriminator (e.g. ``"research"``)."""
        raise NotImplementedError

    @abstractmethod
    def _build_steps(self) -> None:
        """Populate workflow steps via ``self._workflow.add_step(...)``."""
        raise NotImplementedError

    # ── public lifecycle ─────────────────────────────────────────────────

    def start(self, initial_data: dict[str, Any] | None = None) -> str:
        """Start the workflow; returns ``workflow_id``."""
        self._progress_store.init(self._workflow.workflow_id, task_name=self._workflow.name)

        # Wrap step handlers with retry + circuit breaker.
        for step in self._workflow.steps:
            bk = f"{self.workflow_type}/{step.name}"
            original = step.handler
            wrapped = with_retry(
                original,
                policy=self._retry_policy,
                circuit_breaker=self._circuit_breaker,
                breaker_key=bk,
            )
            step.handler = wrapped

        self._workflow.start(initial_data=initial_data)

        # Record metrics after execution.
        self._record_step_metrics()
        self._sync_progress()
        return self._workflow.workflow_id

    def _record_step_metrics(self) -> None:
        opt = self._optimizer
        if opt is None:
            self._latest_optimizer_metrics = {}
            return
        wf_type = self.workflow_type
        for step in self._workflow.steps:
            if step.started_at and step.completed_at:
                dur = (step.completed_at - step.started_at).total_seconds()
                ok = step.status == StepStatus.COMPLETED
                opt.record_step(wf_type, step.name, dur, ok)
        opt.record_workflow(wf_type, self._workflow.state == WorkflowState.COMPLETED)
        summary = opt.summary()
        self._latest_optimizer_metrics = summary.get(wf_type, {})

    def _suggest_timeout(self, step_name: str, default: int = 300) -> int:
        if self._optimizer is None:
            return default
        return self._optimizer.suggest_timeout(self.workflow_type, step_name, default)

    def pause(self) -> None:
        self._workflow.pause()
        self._sync_progress()

    def cancel(self) -> None:
        self._workflow.cancel()
        self._sync_progress()

    def resume(self, approved: bool, feedback: str | None = None) -> dict[str, Any]:
        ctx = self._workflow.resume(approved=approved, feedback=feedback)
        self._sync_progress()
        return ctx.data

    def request_human_intervention(self, message: str) -> None:
        self._workflow.request_human_intervention(message)
        self._sync_progress()

    # ── status / evidence ────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        base = self._workflow.get_status()
        base["workflow_type"] = self.workflow_type
        base["progress"] = self._progress_store.get(self._workflow.workflow_id) or {}
        return base

    def get_evidence(self) -> list[dict[str, Any]]:
        return list(self._workflow.context.history)

    # ── helpers ──────────────────────────────────────────────────────────

    def _sync_progress(self) -> None:
        status = self._workflow.state.value
        step_map = {
            WorkflowState.PENDING: 0,
            WorkflowState.RUNNING: 1,
            WorkflowState.WAITING_HUMAN: 1,
            WorkflowState.COMPLETED: 2,
            WorkflowState.FAILED: 2,
            WorkflowState.CANCELLED: 2,
            WorkflowState.PAUSED: 1,
        }
        idx = step_map.get(self._workflow.state, 0)
        percent = min(100, ((idx) * 100 // 3))
        self._progress_store.update(
            self._workflow.workflow_id,
            step_index=idx,
            message=f"Workflow state: {status}",
            percent=percent,
        )
