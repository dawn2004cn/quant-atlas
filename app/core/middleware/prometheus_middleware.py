"""Flask middleware: record HTTP request Prometheus metrics."""

from __future__ import annotations

import time
from typing import Any

from app.core.logger import get_logger
from app.core.metrics_helpers import normalize_endpoint, record_http_request

logger = get_logger(__name__)


def init_prometheus_middleware(app: Any) -> None:
    """Register before/after hooks to observe request latency and volume."""
    from flask import g, request

    @app.before_request
    def _prometheus_start_timer() -> None:
        g._prometheus_started_at = time.perf_counter()

    @app.after_request
    def _prometheus_record_request(response: Any) -> Any:
        started = getattr(g, "_prometheus_started_at", None)
        if started is None:
            return response
        duration = time.perf_counter() - float(started)
        endpoint = request.endpoint or normalize_endpoint(request.path)
        record_http_request(request.method, endpoint, response.status_code, duration)
        return response

    logger.debug("Prometheus request middleware initialized")


__all__ = ["init_prometheus_middleware"]
