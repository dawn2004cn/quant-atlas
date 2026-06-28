"""OpenTelemetry Tracing Package for Quant Atlas.

Phase 43: 全链路链路追踪 (Distributed Tracing)

This package provides distributed tracing across the entire system:
- HTTP requests (Flask)
- Background tasks (Celery)
- Database operations (SQLAlchemy)
- Business logic (Services)
"""

from .distributed_tracer import DistributedTracer, get_redis_tracer, trace_span
from .opentelemetry import (
    create_span,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    init_opentelemetry,
    trace_ai_analysis,
    trace_factor_calculation,
    trace_market_data_update,
    trace_order_execution,
    trace_signal_generation,
)
from .span_types import SpanType, TraceSpan

__all__ = [
    "init_opentelemetry",
    "get_tracer",
    "create_span",
    "trace_market_data_update",
    "trace_signal_generation",
    "trace_order_execution",
    "trace_factor_calculation",
    "trace_ai_analysis",
    "get_current_trace_id",
    "get_current_span_id",
    "DistributedTracer",
    "get_redis_tracer",
    "trace_span",
    "SpanType",
    "TraceSpan",
]
