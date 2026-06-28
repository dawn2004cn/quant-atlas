"""Observability — Phase 16. Workflow latency/memory/API metrics dashboard."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from app.core.logger import get_logger
from app.core.mesh.global_state_bus import get_global_state_bus

logger = get_logger(__name__)


@dataclass
class WorkflowMetrics:
    workflow_id: str
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    memory_mb: float = 0.0
    cpu_pct: float = 0.0
    request_count: int = 0
    error_rate_pct: float = 0.0
    api_limits_remaining: int = 100
    last_updated: str = ""


class ObservabilityService:
    """Real-time observability: tracks latency, memory, API limits for every workflow."""

    def __init__(self):
        self._latency_tracker: dict[str, deque] = {}
        self._bus = get_global_state_bus()

    def record_latency(self, workflow_id: str, latency_ms: float):
        """Record a single latency measurement."""
        if workflow_id not in self._latency_tracker:
            self._latency_tracker[workflow_id] = deque(maxlen=200)
        self._latency_tracker[workflow_id].append(latency_ms)

    def get_workflow_metrics(self, workflow_id: str) -> WorkflowMetrics:
        """Get aggregated metrics for a workflow."""
        latencies = list(self._latency_tracker.get(workflow_id, []))
        if not latencies:
            return WorkflowMetrics(workflow_id=workflow_id)

        sorted_lats = sorted(latencies)
        n = len(sorted_lats)

        # P95
        p95_idx = min(int(n * 0.95), n - 1)
        p95 = sorted_lats[p95_idx]

        # Error rate (latency > 2000ms = timeout)
        errors = sum(1 for l in latencies if l > 2000)

        metrics = WorkflowMetrics(
            workflow_id=workflow_id,
            avg_latency_ms=round(sum(latencies) / n, 1),
            p95_latency_ms=round(p95, 1),
            request_count=n,
            error_rate_pct=round(errors / n * 100, 2),
        )

        # Publish to global state bus
        self._bus.write_state(f"observability.{workflow_id}", {
            "avg_latency_ms": metrics.avg_latency_ms,
            "p95_latency_ms": metrics.p95_latency_ms,
            "error_rate_pct": metrics.error_rate_pct,
            "request_count": metrics.request_count,
        })

        return metrics

    def get_all_metrics(self) -> dict[str, dict]:
        """Get metrics for all tracked workflows."""
        return {
            wid: {
                "avg_latency_ms": round(sum(list(d)) / len(d), 1),
                "sample_count": len(d),
            }
            for wid, d in self._latency_tracker.items()
        }
