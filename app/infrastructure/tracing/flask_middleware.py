from __future__ import annotations

"""Flask Middleware for OpenTelemetry Trace Propagation.

Phase 43: 全链路链路追踪

This module provides Flask middleware to:
- Extract TraceID from incoming requests
- Inject TraceID into responses
- Create spans for HTTP request handling
- Propagate trace context to downstream services
"""


import logging
from typing import Any

from flask import Flask, g, request
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import SpanKind, Status, StatusCode

from .opentelemetry import get_current_trace_id, get_tracer

logger = logging.getLogger(__name__)


class FlaskTracingMiddleware:
    """Flask middleware for OpenTelemetry trace propagation."""

    def __init__(self, app: Flask | None = None):
        self._app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize middleware with Flask app."""
        self._app = app

        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)

        logger.info("Flask tracing middleware initialized")

    def _before_request(self) -> None:
        """Process request before handling."""
        tracer = get_tracer()

        # Extract trace context from headers
        carrier = {key: value for key, value in request.headers}
        ctx = extract(carrier)

        # Create span for request
        span = tracer.start_as_current_span(
            name=f"{request.method} {request.path}",
            kind=SpanKind.SERVER,
            context=ctx,
        )

        # Set request attributes
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.set_attribute("http.flavor", request.environ.get("SERVER_PROTOCOL"))
        span.set_attribute("http.user_agent", request.headers.get("User-Agent", ""))

        # Store span and context in Flask g
        g.otel_span = span
        g.otel_context = ctx
        g.otel_trace_id = get_current_trace_id()

        # Log trace ID for debugging
        if g.otel_trace_id:
            logger.debug(f"Request trace ID: {g.otel_trace_id}")

    def _after_request(self, response) -> Any:
        """Process response after handling."""
        # Inject trace context into response headers
        if hasattr(g, "otel_span"):
            headers = {}
            inject(headers)
            for key, value in headers.items():
                response.headers[key] = value

            # Set response attributes
            g.otel_span.set_attribute("http.status_code", response.status_code)

            if response.status_code >= 400:
                g.otel_span.set_status(Status(StatusCode.ERROR))
            else:
                g.otel_span.set_status(Status(StatusCode.OK))

        return response

    def _teardown_request(self, exception) -> None:
        """Clean up after request."""
        if hasattr(g, "otel_span"):
            if exception:
                g.otel_span.set_status(Status(StatusCode.ERROR, str(exception)))
                g.otel_span.record_exception(exception)
            g.otel_span.end()


def init_flask_tracing(app: Flask) -> None:
    """Factory function to initialize Flask tracing."""
    FlaskTracingMiddleware(app)


__all__ = [
    "FlaskTracingMiddleware",
    "init_flask_tracing",
]
