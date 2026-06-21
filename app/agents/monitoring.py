from __future__ import annotations
"""Agent Monitoring & Observability - OpenTelemetry Integration.

This module implements from midify_plan13.md optimization:
- AgentTelemetry: OpenTelemetry tracing for agent calls
- Metrics: Token consumption, latency, success rate
- Dashboard: Real-time agent health visualization

Usage:
    telemetry = AgentTelemetry()
    with telemetry.trace("technical_agent"):
        result = await agent.execute()
"""


import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from contextlib import asynccontextmanager
from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentMetrics:
    """Metrics for a single agent."""
    agent_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0


@dataclass
class AgentSpan:
    """Trace span for agent execution."""
    span_id: str
    agent_name: str
    start_time: datetime
    end_time: datetime | None = None
    tokens_used: int = 0
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentTelemetry:
    """OpenTelemetry-style tracing for agent system.

    Tracks:
    - Call latency
    - Token consumption
    - Success/failure rates
    - Agent dependencies
    """

    def __init__(self, service_name: str = "quant-agent"):
        self._service_name = service_name
        self._spans: list[AgentSpan] = []
        self._metrics: dict[str, AgentMetrics] = {}
        self._active_spans: dict[str, AgentSpan] = {}

    @asynccontextmanager
    async def trace(self, agent_name: str, metadata: dict[str, Any] | None = None):
        """Trace agent execution."""
        import uuid
        span_id = str(uuid.uuid4())[:8]

        span = AgentSpan(
            span_id=span_id,
            agent_name=agent_name,
            start_time=datetime.now(),
            metadata=metadata or {},
        )

        self._active_spans[span_id] = span
        start_time = time.time()

        try:
            yield span
            span.status = "success"
        except Exception as e:
            span.status = "error"
            span.metadata["error"] = str(e)
            raise
        finally:
            end_time = time.time()
            span.end_time = datetime.now()
            latency_ms = (end_time - start_time) * 1000

            span.metadata["latency_ms"] = latency_ms

            self._record_metrics(agent_name, span, latency_ms)
            del self._active_spans[span_id]

    def _record_metrics(self, agent_name: str, span: AgentSpan, latency_ms: float) -> None:
        """Record metrics for agent."""
        if agent_name not in self._metrics:
            self._metrics[agent_name] = AgentMetrics(agent_name=agent_name)

        metrics = self._metrics[agent_name]
        metrics.total_calls += 1

        if span.status == "success":
            metrics.successful_calls += 1
        else:
            metrics.failed_calls += 1

        metrics.total_latency_ms += latency_ms
        metrics.avg_latency_ms = metrics.total_latency_ms / metrics.total_calls

    def record_tokens(self, agent_name: str, tokens: int) -> None:
        """Record token usage for agent."""
        if agent_name not in self._metrics:
            self._metrics[agent_name] = AgentMetrics(agent_name=agent_name)
        self._metrics[agent_name].total_tokens += tokens

    def get_agent_metrics(self, agent_name: str) -> AgentMetrics | None:
        """Get metrics for specific agent."""
        return self._metrics.get(agent_name)

    def get_all_metrics(self) -> dict[str, AgentMetrics]:
        """Get all agent metrics."""
        return self._metrics.copy()

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get data for monitoring dashboard."""
        total_calls = sum(m.total_calls for m in self._metrics.values())
        total_success = sum(m.successful_calls for m in self._metrics.values())
        success_rate = total_success / total_calls if total_calls > 0 else 0

        total_tokens = sum(m.total_tokens for m in self._metrics.values())
        avg_latency = sum(m.avg_latency_ms for m in self._metrics.values()) / len(self._metrics) if self._metrics else 0

        return {
            "total_calls": total_calls,
            "success_rate": f"{success_rate * 100:.1f}%",
            "total_tokens": total_tokens,
            "avg_latency_ms": f"{avg_latency:.0f}",
            "agents": {
                name: {
                    "calls": m.total_calls,
                    "success_rate": f"{m.successful_calls / m.total_calls * 100:.1f}%" if m.total_calls > 0 else "0%",
                    "tokens": m.total_tokens,
                    "avg_latency_ms": f"{m.avg_latency_ms:.0f}",
                }
                for name, m in self._metrics.items()
            },
            "active_spans": len(self._active_spans),
        }


class AgentMonitor:
    """Agent monitoring with periodic reporting."""

    def __init__(self, telemetry: AgentTelemetry | None = None):
        self._telemetry = telemetry or AgentTelemetry()

    async def monitor_agent(
        self,
        agent_name: str,
        func,
        *args,
        **kwargs,
    ) -> Any:
        """Monitor agent execution with telemetry."""
        async with self._telemetry.trace(agent_name):
            result = await func(*args, **kwargs)
            return result


_global_telemetry: AgentTelemetry | None = None


def get_telemetry() -> AgentTelemetry:
    """Get singleton telemetry."""
    global _global_telemetry
    if _global_telemetry is None:
        _global_telemetry = AgentTelemetry()
    return _global_telemetry