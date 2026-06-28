from __future__ import annotations

"""Monitoring & Observability for Domain Layer.

Metrics, structured logging, and tracing.
"""


import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: dict = field(default_factory=dict)


class MetricsCollector:
    """Collects metrics for domain operations."""

    def __init__(self):
        self._metrics: dict[str, list[MetricPoint]] = {}
        self._counters: dict[str, int] = {}

    def record(self, name: str, value: float, tags: dict = None) -> None:
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(MetricPoint(name, value, tags=tags or {}))

    def increment(self, name: str, delta: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + delta

    def gauge(self, name: str, value: float) -> None:
        self.record(name, value)

    def timing(self, name: str, duration_ms: float) -> None:
        self.record(f"{name}.timing", duration_ms)

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_metrics(self, name: str) -> list[MetricPoint]:
        return self._metrics.get(name, [])

    def get_all_counters(self) -> dict[str, int]:
        return self._counters.copy()

    def clear(self) -> None:
        self._metrics.clear()
        self._counters.clear()


class StructuredLogger:
    """Structured logging for domain operations."""

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def log(
        self,
        level: str,
        message: str,
        extra: dict = None,
        **kwargs
    ) -> None:
        log_data = {
            "message": message,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        if extra:
            log_data.update(extra)

        getattr(self._logger, level)(str(log_data))

    def debug(self, message: str, **kwargs) -> None:
        self.log("debug", message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self.log("info", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self.log("warning", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self.log("error", message, **kwargs)


class RequestTracer:
    """Simple request tracing."""

    def __init__(self):
        self._traces: list[dict] = []
        self._max_traces = 1000

    def start_trace(self, request_id: str, operation: str) -> str:
        trace = {
            "request_id": request_id,
            "operation": operation,
            "start_time": time.time(),
            "spans": [],
        }
        self._traces.append(trace)
        return request_id

    def start_span(self, trace_id: str, span_name: str) -> str:
        span_id = f"{trace_id}.{len(self._traces[-1]['spans'])}"
        self._traces[-1]["spans"].append({
            "name": span_name,
            "start_time": time.time(),
        })
        return span_id

    def end_span(self, trace_id: str, span_id: str) -> None:
        trace = self._traces[-1]
        if trace["request_id"] == trace_id:
            for span in trace["spans"]:
                if span["name"] == span_id:
                    span["duration"] = time.time() - span["start_time"]
                    break

    def end_trace(self, request_id: str) -> None:
        for trace in self._traces:
            if trace["request_id"] == request_id:
                trace["end_time"] = time.time()
                trace["total_duration"] = trace["end_time"] - trace["start_time"]
                break

    def get_trace(self, request_id: str) -> dict | None:
        for trace in self._traces:
            if trace["request_id"] == request_id:
                return trace
        return None

    def get_recent(self, limit: int = 10) -> list[dict]:
        return self._traces[-limit:]


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    global _metrics_collector
    if not hasattr(get_metrics_collector, '_instance'):
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_tracer() -> RequestTracer:
    """Get global tracer."""
    global _tracer
    if not hasattr(get_tracer, '_instance'):
        _tracer = RequestTracer()
    return _tracer


__all__ = [
    "MetricPoint",
    "MetricsCollector",
    "StructuredLogger",
    "RequestTracer",
    "get_metrics_collector",
    "get_tracer",
]
