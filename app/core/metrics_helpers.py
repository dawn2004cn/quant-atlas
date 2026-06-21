"""Helpers to record Prometheus metrics with graceful no-op degradation."""

from __future__ import annotations

import functools
import re
import time
from typing import Any

_ROUTE_PARAM_RE = re.compile(
    r"/(?:\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?=/|$)",
    re.IGNORECASE,
)
_SYMBOL_RE = re.compile(r"/\d{6}(?:\.(?:SH|SZ|HK))?(?=/|$)", re.IGNORECASE)


def normalize_endpoint(path: str) -> str:
    """Collapse dynamic path segments to limit Prometheus label cardinality."""
    if not path:
        return "unknown"
    if path.startswith("/static"):
        return "/static"
    normalized = _SYMBOL_RE.sub("/{symbol}", path)
    normalized = _ROUTE_PARAM_RE.sub("/{id}", normalized)
    return normalized[:120]


def record_http_request(method: str, endpoint: str, status: int, duration_seconds: float) -> None:
    """Record HTTP request count, duration, and server errors."""
    from app.core.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_DURATION

    status_str = str(status)
    if REQUEST_COUNT is not None:
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_str).inc()
    if REQUEST_DURATION is not None:
        REQUEST_DURATION.labels(method=method, endpoint=endpoint, status=status_str).observe(
            duration_seconds
        )
    if status >= 500 and ERROR_COUNT is not None:
        ERROR_COUNT.labels(error_type="http_5xx", endpoint=endpoint).inc()


def record_ai_call(model: str, call_type: str, duration_seconds: float) -> None:
    """Record AI/LLM invocation metrics."""
    from app.core.metrics import AI_CALL_DURATION, AI_CALLS_TOTAL

    model_label = (model or "unknown")[:64]
    if AI_CALLS_TOTAL is not None:
        AI_CALLS_TOTAL.labels(model=model_label, call_type=call_type).inc()
    if AI_CALL_DURATION is not None:
        AI_CALL_DURATION.labels(model=model_label, call_type=call_type).observe(duration_seconds)


def record_backtest_completed(*, engine: str, outcome: str) -> None:
    """Increment backtest completion counter."""
    from app.core.metrics import BACKTEST_COMPLETED

    if BACKTEST_COMPLETED is not None:
        BACKTEST_COMPLETED.labels(engine=engine, outcome=outcome).inc()


def instrument_chat_model(model: Any, *, model_name: str, call_type: str = "chat") -> Any:
    """Wrap LangChain chat model ``invoke`` / ``ainvoke`` with timing metrics."""
    if getattr(model, "_metrics_instrumented", False):
        return model

    label = (model_name or getattr(model, "model_name", None) or "unknown")[:64]

    if hasattr(model, "invoke"):
        original_invoke = model.invoke

        @functools.wraps(original_invoke)
        def timed_invoke(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return original_invoke(*args, **kwargs)
            finally:
                record_ai_call(label, call_type, time.perf_counter() - start)

        model.invoke = timed_invoke  # type: ignore[method-assign]

    if hasattr(model, "ainvoke"):
        original_ainvoke = model.ainvoke

        @functools.wraps(original_ainvoke)
        async def timed_ainvoke(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return await original_ainvoke(*args, **kwargs)
            finally:
                record_ai_call(label, call_type, time.perf_counter() - start)

        model.ainvoke = timed_ainvoke  # type: ignore[method-assign]

    model._metrics_instrumented = True  # type: ignore[attr-defined]
    return model


__all__ = [
    "normalize_endpoint",
    "record_http_request",
    "record_ai_call",
    "record_backtest_completed",
    "instrument_chat_model",
]
