from __future__ import annotations

"""Distributed tracing integration for quant-atlas.

Lightweight context-var based trace ID propagation is always available.
OpenTelemetry support is opt-in: activates when setup_otel() is called
and the opentelemetry SDK is installed.
"""

import contextvars
import uuid
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Lightweight trace ID propagation (contextvars) — always available
# ---------------------------------------------------------------------------

_trace_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)


def set_trace_id(trace_id: str | None = None) -> str:
    """Set the trace ID for the current context."""
    tid = trace_id or uuid.uuid4().hex
    _trace_id_ctx.set(tid)
    return tid


def get_trace_id() -> str | None:
    """Get the current trace ID, searching both thread-local and contextvar."""
    val = _trace_id_ctx.get()
    return val


def get_context_snapshot() -> dict[contextvars.ContextVar, Any]:
    """Capture current context variables for propagation."""
    return {_trace_id_ctx: _trace_id_ctx.get()}


def restore_context(snapshot: dict[contextvars.ContextVar, Any]):
    """Restore context variables in a child thread/context."""
    for var, value in snapshot.items():
        var.set(value)


# ---------------------------------------------------------------------------
# OpenTelemetry integration — opt-in
# ---------------------------------------------------------------------------

try:
    from opentelemetry import trace as _otel_trace
    from opentelemetry.sdk.trace import TracerProvider as _OtelProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor as _BatchSpanProcessor,
    )
    from opentelemetry.sdk.trace.export import (
        ConsoleSpanExporter as _ConsoleSpanExporter,
    )

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False


def setup_otel(
    service_name: str = "quant-atlas",
    jaeger_endpoint: str | None = None,
    console_export: bool = False,
) -> None:
    """Set up OpenTelemetry tracing.

    Args:
        service_name: Service name for trace identification.
        jaeger_endpoint: Jaeger collector endpoint
            (e.g., http://localhost:14268/api/traces).
        console_export: If True, export spans to console (for debugging).
    """
    if not HAS_OTEL:
        return  # OpenTelemetry not installed
    if not service_name:
        return  # No service name = no tracing

    provider = _OtelProvider(service_name=service_name)

    if jaeger_endpoint:
        try:
            import logging

            from opentelemetry.exporter.jaeger.thrift import JaegerExporter

            logger = logging.getLogger(__name__)

            exporter = JaegerExporter(endpoint=jaeger_endpoint)
            provider.add_span_processor(_BatchSpanProcessor(exporter))
        except ImportError:
            logger.warning("Suppressed exception", exc_info=True)
            pass  # Jaeger exporter not available

    if console_export:
        provider.add_span_processor(
            _BatchSpanProcessor(_ConsoleSpanExporter())
        )

    _otel_trace.set_tracer_provider(provider)


def get_tracer(name: str):
    """Get a tracer by name, or None if OTel not configured or unavailable."""
    if not HAS_OTEL:
        return None
    return _otel_trace.get_tracer(name)
