from __future__ import annotations

"""Celery Tasks for OpenTelemetry Tracing.

Phase 43: 全链路链路追踪

This module provides:
- Tracing initialization tasks
- Trace context propagation utilities
- Periodic trace export tasks
"""


import logging
from typing import Any

from app.celery_app import celery_app
from app.tasks.task_wiring import get_current_trace_id, init_opentelemetry

logger = logging.getLogger(__name__)


@celery_app.task(name="tracing.initialize_tracer", bind=True)
def initialize_tracer_task(
    self,
    service_name: str = "quant-atlas-worker",
    jaeger_endpoint: str = None,
    console_export: bool = False,
) -> dict[str, Any]:
    """Initialize OpenTelemetry tracer in Celery worker.

    Args:
        service_name: Service name for tracing
        jaeger_endpoint: Jaeger collector endpoint
        console_export: Whether to export spans to console

    Returns:
        Tracer initialization status
    """
    try:
        tracer = init_opentelemetry(
            service_name=service_name,
            jaeger_endpoint=jaeger_endpoint,
            console_export=console_export,
        )

        return {
            "status": "success",
            "service_name": service_name,
            "tracer": str(tracer),
        }
    except Exception as e:
        logger.error(f"Failed to initialize tracer: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@celery_app.task(name="tracing.export_pending_spans")
def export_pending_spans_task() -> dict[str, Any]:
    """Force export of pending spans to backend.

    Returns:
        Export status
    """
    try:

        # Get tracer provider
        from opentelemetry import trace
        provider = trace.get_tracer_provider()

        # Force flush all pending spans
        if hasattr(provider, "force_flush"):
            provider.force_flush(timeout_millis=5000)

        return {
            "status": "success",
            "message": "Pending spans exported",
        }
    except Exception as e:
        logger.error(f"Failed to export pending spans: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@celery_app.task(name="tracing.get_trace_context")
def get_trace_context_task() -> dict[str, Any]:
    """Get current trace context for debugging.

    Returns:
        Current trace context
    """
    return {
        "trace_id": get_current_trace_id() or "no_active_trace",
        "status": "success",
    }


__all__ = [
    "initialize_tracer_task",
    "export_pending_spans_task",
    "get_trace_context_task",
]
