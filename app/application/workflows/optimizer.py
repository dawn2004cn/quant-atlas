from __future__ import annotations
"""Workflow optimizer — track execution metrics and adapt parameters.

Records per-(workflow_type, step_name) stats and adjusts timeouts
based on historical P95 durations.
"""


import statistics
import threading
from dataclasses import dataclass, field
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StepMetrics:
    """Metrics collected for a single workflow step."""

    durations_s: list[float] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    last_duration_s: float = 0.0
    suggested_timeout_s: int = 300

    def record(self, duration_s: float, success: bool) -> None:
        self.durations_s.append(duration_s)
        self.last_duration_s = duration_s
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        # Keep a sliding window of the last 50 durations.
        if len(self.durations_s) > 50:
            self.durations_s = self.durations_s[-50:]

    @property
    def p95_duration_s(self) -> float:
        if len(self.durations_s) < 3:
            return self.last_duration_s or 30.0
        sorted_d = sorted(self.durations_s)
        idx = int(len(sorted_d) * 0.95)
        return sorted_d[min(idx, len(sorted_d) - 1)]

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def adaptive_timeout(self) -> int:
        """Return a timeout value (seconds) based on historical P95 + 20% buffer."""
        return max(60, int(self.p95_duration_s * 1.2) + 10)


@dataclass
class WorkflowMetrics:
    """Aggregate metrics for a workflow type."""

    workflow_type: str
    steps: dict[str, StepMetrics] = field(default_factory=dict)
    total_runs: int = 0
    total_success: int = 0
    total_failure: int = 0

    def record_run(self, success: bool) -> None:
        self.total_runs += 1
        if success:
            self.total_success += 1
        else:
            self.total_failure += 1

    def step(self, name: str) -> StepMetrics:
        if name not in self.steps:
            self.steps[name] = StepMetrics()
        return self.steps[name]


class WorkflowOptimizer:
    """Tracks execution metrics across all workflow types.

    Thread-safe for concurrent workflow executions.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics: dict[str, WorkflowMetrics] = {}

    # ── recording ─────────────────────────────────────────────────────────

    def record_step(
        self,
        workflow_type: str,
        step_name: str,
        duration_s: float,
        success: bool,
    ) -> None:
        with self._lock:
            wm = self._metrics.setdefault(workflow_type, WorkflowMetrics(workflow_type=workflow_type))
            wm.step(step_name).record(duration_s, success)

    def record_workflow(self, workflow_type: str, success: bool) -> None:
        with self._lock:
            wm = self._metrics.setdefault(workflow_type, WorkflowMetrics(workflow_type=workflow_type))
            wm.record_run(success)

    # ── query ─────────────────────────────────────────────────────────────

    def get_metrics(self, workflow_type: str) -> WorkflowMetrics | None:
        return self._metrics.get(workflow_type)

    def get_step_metrics(self, workflow_type: str, step_name: str) -> StepMetrics | None:
        wm = self._metrics.get(workflow_type)
        if wm is None:
            return None
        return wm.steps.get(step_name)

    def suggest_timeout(self, workflow_type: str, step_name: str, default: int = 300) -> int:
        sm = self.get_step_metrics(workflow_type, step_name)
        if sm is None or len(sm.durations_s) < 3:
            return default
        return sm.adaptive_timeout()

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                wf_type: {
                    "total_runs": wm.total_runs,
                    "success_rate": wm.total_success / max(wm.total_runs, 1),
                    "steps": {
                        sname: {
                            "n": len(sm.durations_s),
                            "success_rate": sm.success_rate,
                            "avg_duration_s": statistics.mean(sm.durations_s) if sm.durations_s else 0,
                            "p95_duration_s": sm.p95_duration_s,
                            "suggested_timeout_s": sm.adaptive_timeout(),
                        }
                        for sname, sm in wm.steps.items()
                    },
                }
                for wf_type, wm in self._metrics.items()
            }
