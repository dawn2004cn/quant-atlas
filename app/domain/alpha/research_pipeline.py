from __future__ import annotations
"""Physical Research Pipeline - Drift to Alpha Bridge.

Implements from strategy_plan3.md Phase 2:
- Physical pipeline: Drift -> RD-Agent -> Qlib -> New AlphaEntity
- TCA feedback integration
- Unattended research loop

Usage:
    pipeline = PhysicalPipeline()
    task_id = pipeline.trigger_research(drift_report)
    alpha = pipeline.wait_for_alpha(task_id)
"""


import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from app.core.logger import get_logger

logger = get_logger(__name__)


class PipelineState(Enum):
    """State of research pipeline."""
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResearchTask:
    """Research task in pipeline."""
    task_id: str
    drift_report: dict[str, Any]
    target_metrics: dict[str, float]
    status: PipelineState = PipelineState.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    alpha_id: str | None = None
    error: str | None = None


@dataclass
class PipelineConfig:
    """Configuration for research pipeline."""
    max_parallel_tasks: int = 3
    task_timeout_minutes: int = 60
    min_ic_threshold: float = 0.02
    min_sharpe_threshold: float = 0.5
    correlation_threshold: float = 0.8


class PhysicalPipeline:
    """Physical pipeline connecting drift to RD-Agent research."""

    def __init__(self, config: PipelineConfig | None = None):
        self._config = config or PipelineConfig()
        self._tasks: dict[str, ResearchTask] = {}
        self._pending_tasks: list[str] = []
        self._completed_tasks: list[str] = []
        self._callbacks: list[Callable] = []
        self._tca_calibrator = None

    def trigger_research(
        self,
        drift_report: dict[str, Any],
        target_ic: float = None,
        target_sharpe: float = None,
    ) -> str:
        """Trigger RD-Agent research from drift report."""
        task_id = str(uuid4())[:8]

        target_metrics = {
            "ic": target_ic or self._config.min_ic_threshold,
            "sharpe": target_sharpe or self._config.min_sharpe_threshold,
        }

        task = ResearchTask(
            task_id=task_id,
            drift_report=drift_report,
            target_metrics=target_metrics,
            status=PipelineState.QUEUED,
        )

        self._tasks[task_id] = task
        self._pending_tasks.append(task_id)

        logger.info(f"Queued research task {task_id}: {drift_report.get('cause', 'unknown')}")

        self._process_task_async(task_id)

        return task_id

    def _process_task_async(self, task_id: str) -> None:
        """Process task asynchronously."""
        import threading

        def run():
            try:
                self._execute_task(task_id)
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                self._tasks[task_id].status = PipelineState.FAILED
                self._tasks[task_id].error = str(e)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _execute_task(self, task_id: str) -> None:
        """Execute research task."""
        task = self._tasks.get(task_id)
        if not task:
            return

        task.status = PipelineState.RUNNING
        task.started_at = datetime.now()

        logger.info(f"Starting research task {task_id}")

        alpha_id = self._run_rdagent_research(task)

        task.alpha_id = alpha_id
        task.status = PipelineState.COMPLETED
        task.completed_at = datetime.now()

        self._completed_tasks.append(task_id)

        for callback in self._callbacks:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"Callback failed: {e}")

        logger.info(f"Research task {task_id} completed: alpha={alpha_id}")

    def _run_rdagent_research(self, task: ResearchTask) -> str | None:
        """Run RD-Agent research via domain port (DIP)."""
        try:
            from app.domain.ports.rdagent_ports import RDAgentValidationPort

            rd_agent = RDAgentValidationPort()
            if not hasattr(rd_agent, "run_research"):
                return None
            result = rd_agent.run_research  # type: ignore[attr-defined]
            if callable(result):
                return result(
                    objective=task.drift_report.get("cause", "factor_drift"),
                    constraints={
                        "min_ic": task.target_metrics["ic"],
                        "min_sharpe": task.target_metrics["sharpe"],
                    },
                )  # type: ignore[attr-defined]

        except ImportError:
            logger.warning("RDAgentRunService not available, using mock")

            return f"alpha_{task.task_id}"

    def get_alpha(
        self,
        task_id: str,
    ) -> dict[str, Any] | None:
        """Get alpha from completed task."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        if task.status != PipelineState.COMPLETED:
            return None

        return {
            "alpha_id": task.alpha_id,
            "task_id": task_id,
            "target_metrics": task.target_metrics,
            "created_at": task.completed_at,
        }

    def wait_for_alpha(
        self,
        task_id: str,
        timeout_seconds: int = 3600,
    ) -> dict[str, Any] | None:
        """Wait for alpha from task."""
        import time

        start = time.time()

        while time.time() - start < timeout_seconds:
            alpha = self.get_alpha(task_id)
            if alpha:
                return alpha

            task = self._tasks.get(task_id)
            if task and task.status == PipelineState.FAILED:
                return None

            time.sleep(1)

        return None

    def register_callback(
        self,
        callback: Callable,
    ) -> None:
        """Register callback for completed tasks."""
        self._callbacks.append(callback)

    def get_task_status(
        self,
        task_id: str,
    ) -> PipelineState | None:
        """Get task status."""
        task = self._tasks.get(task_id)
        return task.status if task else None

    def get_pending_count(self) -> int:
        """Get pending task count."""
        return len(self._pending_tasks)

    def get_stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        states = {}
        for task in self._tasks.values():
            state = task.status.value
            states[state] = states.get(state, 0) + 1

        return {
            "total_tasks": len(self._tasks),
            "pending": len(self._pending_tasks),
            "completed": len(self._completed_tasks),
            "states": states,
        }


class AutonomousResearchLoop:
    """Autonomous loop connecting drift detection to research."""

    def __init__(self, pipeline: PhysicalPipeline = None):
        self._pipeline = pipeline or PhysicalPipeline()
        self._pipeline.register_callback(self._on_alpha_complete)
        self._recent_alphas: list[dict] = []

    def run_cycle(
        self,
        drift_report: dict[str, Any],
    ) -> str:
        """Run one autonomous research cycle."""
        task_id = self._pipeline.trigger_research(drift_report)
        logger.info(f"Autonomous cycle started: task={task_id}")
        return task_id

    def _on_alpha_complete(self, task: ResearchTask) -> None:
        """Handle completed alpha."""
        self._recent_alphas.append({
            "alpha_id": task.alpha_id,
            "task_id": task.task_id,
            "timestamp": task.completed_at,
        })

        self._recent_alphas = self._recent_alphas[-100:]

    def get_recent_alphas(self, count: int = 10) -> list[dict]:
        """Get recent completed alphas."""
        return self._recent_alphas[-count:]


_global_pipeline: PhysicalPipeline | None = None


def get_research_pipeline() -> PhysicalPipeline:
    """Get global research pipeline."""
    global _global_pipeline
    if _global_pipeline is None:
        _global_pipeline = PhysicalPipeline()
    return _global_pipeline