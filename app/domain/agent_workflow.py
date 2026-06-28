from __future__ import annotations

"""Agent Workflow State Machine for complex task orchestration."""


from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class WorkflowState(Enum):
    """States in the agent workflow."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    """Status of individual workflow steps."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


@dataclass
class WorkflowStep:
    """Individual step in the workflow."""
    name: str
    handler: Callable  # The actual function to execute
    required: bool = True
    timeout: int = 300  # seconds
    retry_on_failure: int = 2

    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class WorkflowContext:
    """Context passed between workflow steps."""
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    def add_history(self, step: str, result: Any, status: str) -> None:
        """Add step execution to history."""
        self.history.append({
            "step": step,
            "result": str(result)[:200],
            "status": status,
            "timestamp": datetime.now().isoformat()
        })


@dataclass
class AgentWorkflow:
    """State machine for agent workflow orchestration."""

    workflow_id: str
    name: str
    steps: list[WorkflowStep] = field(default_factory=list)

    state: WorkflowState = WorkflowState.PENDING
    current_step_index: int = 0
    context: WorkflowContext = field(default_factory=WorkflowContext)

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Callbacks
    on_step_complete: Callable | None = None
    on_step_fail: Callable | None = None
    on_human介入: Callable | None = None

    def add_step(
        self,
        name: str,
        handler: Callable,
        required: bool = True,
        timeout: int = 300
    ) -> AgentWorkflow:
        """Add a step to the workflow."""
        step = WorkflowStep(
            name=name,
            handler=handler,
            required=required,
            timeout=timeout
        )
        self.steps.append(step)
        return self

    def start(self, initial_data: dict[str, Any] | None = None) -> WorkflowContext:
        """Start the workflow."""
        if self.state not in (WorkflowState.PENDING, WorkflowState.PAUSED):
            raise ValueError(f"Cannot start workflow in state: {self.state}")

        self.state = WorkflowState.RUNNING
        self.current_step_index = 0
        self.context = WorkflowContext(data=initial_data or {})
        self.updated_at = datetime.now()

        logger.info(f"Workflow {self.workflow_id} started")
        return self._execute_current_step()

    def _execute_current_step(self) -> WorkflowContext:
        """Execute the current step."""
        if self.current_step_index >= len(self.steps):
            return self._complete()

        step = self.steps[self.current_step_index]
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()

        logger.info(f"Executing step: {step.name}")

        try:
            result = step.handler(self.context)
            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now()

            self.context.add_history(step.name, result, "completed")

            if self.on_step_complete:
                self.on_step_complete(self, step)

            # Move to next step
            self.current_step_index += 1
            self.updated_at = datetime.now()

            return self._execute_current_step()

        except Exception as e:
            logger.error(f"Step {step.name} failed: {e}")
            step.error = str(e)
            step.status = StepStatus.FAILED

            if step.retry_on_failure > 0:
                step.retry_on_failure -= 1
                logger.info(f"Retrying step {step.name}, remaining retries: {step.retry_on_failure}")
                return self._execute_current_step()

            self.context.add_history(step.name, str(e), "failed")

            if step.required:
                return self._fail(str(e))
            else:
                self.current_step_index += 1
                return self._execute_current_step()

    def _complete(self) -> WorkflowContext:
        """Complete the workflow."""
        self.state = WorkflowState.COMPLETED
        self.updated_at = datetime.now()
        logger.info(f"Workflow {self.workflow_id} completed")
        return self.context

    def _fail(self, error: str) -> WorkflowContext:
        """Fail the workflow."""
        self.state = WorkflowState.FAILED
        self.context.metadata["error"] = error
        self.updated_at = datetime.now()
        logger.error(f"Workflow {self.workflow_id} failed: {error}")
        return self.context

    def pause(self) -> None:
        """Pause the workflow."""
        self.state = WorkflowState.PAUSED
        self.updated_at = datetime.now()

    def cancel(self) -> None:
        """Cancel the workflow."""
        self.state = WorkflowState.CANCELLED
        self.updated_at = datetime.now()

    def request_human_intervention(self, message: str) -> None:
        """Request human intervention."""
        self.state = WorkflowState.WAITING_HUMAN
        self.context.metadata["human_request"] = message
        self.updated_at = datetime.now()

        if self.on_human介入:
            self.on_human介入(self, message)

    def resume(self, approved: bool, feedback: str | None = None) -> WorkflowContext:
        """Resume after human intervention."""
        if self.state != WorkflowState.WAITING_HUMAN:
            raise ValueError("Workflow is not waiting for human intervention")

        if not approved:
            return self._fail(feedback or "Human rejected")

        self.state = WorkflowState.RUNNING
        self.context.metadata.pop("human_request", None)

        if feedback:
            self.context.data["human_feedback"] = feedback

        return self._execute_current_step()

    def get_status(self) -> dict[str, Any]:
        """Get current workflow status."""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "state": self.state.value,
            "current_step": self.steps[self.current_step_index].name if self.current_step_index < len(self.steps) else None,
            "progress": f"{self.current_step_index}/{len(self.steps)}",
            "context_keys": list(self.context.data.keys()),
            "history_count": len(self.context.history)
        }


class WorkflowBuilder:
    """Builder for creating workflows."""

    def __init__(self, workflow_id: str, name: str):
        self.workflow = AgentWorkflow(workflow_id=workflow_id, name=name)

    def add_step(self, name: str, handler: Callable, required: bool = True, timeout: int = 300):
        self.workflow.add_step(name, handler, required, timeout)
        return self

    def on_complete(self, callback: Callable):
        self.workflow.on_step_complete = callback
        return self

    def on_fail(self, callback: Callable):
        self.workflow.on_step_fail = callback
        return self

    def on_human(self, callback: Callable):
        self.workflow.on_human介入 = callback
        return self

    def build(self) -> AgentWorkflow:
        return self.workflow


__all__ = [
    "WorkflowState",
    "StepStatus",
    "WorkflowStep",
    "WorkflowContext",
    "AgentWorkflow",
    "WorkflowBuilder"
]
