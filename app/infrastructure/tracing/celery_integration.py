from __future__ import annotations

"""Celery Integration for OpenTelemetry Trace Propagation.

Phase 43: 全链路链路追踪

This module provides Celery integration to:
- Propagate trace context from producer to consumer
- Create spans for task execution
- Link task spans to parent traces
"""


import logging
from collections.abc import Callable
from functools import wraps

from celery import Celery, signals
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import SpanKind, Status, StatusCode

from .opentelemetry import get_current_trace_id, get_tracer

logger = logging.getLogger(__name__)


class CeleryTracingMiddleware:
    """Celery middleware for OpenTelemetry trace propagation."""

    def __init__(self, app: Celery | None = None):
        self._app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Celery) -> None:
        """Initialize middleware with Celery app."""
        self._app = app

        # Connect to Celery signals
        signals.before_task_publish.connect(self._before_task_publish)
        signals.after_task_publish.connect(self._after_task_publish)
        signals.task_prerun.connect(self._task_prerun)
        signals.task_postrun.connect(self._task_postrun)
        signals.task_failure.connect(self._task_failure)

        logger.info("Celery tracing middleware initialized")

    def _before_task_publish(self, sender=None, headers=None, body=None, **kwargs):
        """Inject trace context before task is published."""
        if headers is None:
            headers = {}

        # Inject current trace context into headers
        carrier = {}
        inject(carrier)
        headers.update(carrier)

        logger.debug(f"Injected trace context into task: {sender}")

    def _after_task_publish(self, sender=None, headers=None, body=None, **kwargs):
        """Clean up after task is published."""
        pass

    def _task_prerun(self, task_id=None, task=None, args=None, kwargs=None, **kwargs_extra):
        """Extract trace context and create span before task runs."""
        tracer = get_tracer()

        # Extract trace context from task headers
        carrier = task.request.get("headers", {})
        ctx = extract(carrier)

        # Create span for task execution
        span = tracer.start_as_current_span(
            name=f"celery.{task.name}",
            kind=SpanKind.CONSUMER,
            context=ctx,
        )

        # Set task attributes
        span.set_attribute("celery.task_id", task_id)
        span.set_attribute("celery.task_name", task.name)
        span.set_attribute("celery.args", str(args)[:1000] if args else "")
        span.set_attribute("celery.kwargs", str(kwargs)[:1000] if kwargs else "")

        # Store span in task context
        task.request._otel_span = span
        task.request._otel_trace_id = get_current_trace_id()

        logger.debug(f"Task {task.name} started with trace ID: {task.request._otel_trace_id}")

    def _task_postrun(self, task_id=None, task=None, state=None, retval=None, **kwargs):
        """End span after task completes."""
        if hasattr(task.request, "_otel_span"):
            span = task.request._otel_span

            if state == "SUCCESS":
                span.set_status(Status(StatusCode.OK))
            elif state == "FAILURE":
                span.set_status(Status(StatusCode.ERROR, str(retval)))

            span.end()

    def _task_failure(self, task_id=None, exception=None, traceback=None, **kwargs):
        """Record exception on task failure."""
        # This is handled by _task_postrun, but we can add additional logic here
        pass


def trace_task(func: Callable) -> Callable:
    """Decorator to trace Celery task execution.

    Usage:
        @app.task
        @trace_task
        def my_task(arg1, arg2):
            # Task logic here
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        tracer = get_tracer()

        with tracer.start_as_current_span(
            name=f"task.{func.__name__}",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("task.name", func.__name__)
            span.set_attribute("task.args", str(args)[:1000] if args else "")
            span.set_attribute("task.kwargs", str(kwargs)[:1000] if kwargs else "")

            try:
                result = func(*args, **kwargs)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    return wrapper


def init_celery_tracing(app: Celery) -> None:
    """Factory function to initialize Celery tracing."""
    CeleryTracingMiddleware(app)


__all__ = [
    "CeleryTracingMiddleware",
    "trace_task",
    "init_celery_tracing",
]
