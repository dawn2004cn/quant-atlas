from __future__ import annotations
"""Distributed tracing integration using OpenTelemetry concepts."""

import uuid
import contextvars
from typing import Any

# Context variable to hold the current TraceID
_trace_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)

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
