from __future__ import annotations

"""Redis-backed distributed tracer for decision path visibility."""

import json
import uuid
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

import redis

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.infrastructure.redis_client import RedisClientPool

from .span_store import (
    TRACE_TTL,
    load_trace,
    span_key,
    store_span,
)
from .span_types import SpanType, TraceSpan

logger = get_logger(__name__)


class DistributedTracer:
    """Distributed tracing system for decision paths (Redis persistence)."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or get_runtime("REDIS_URL", "")
        self._client: redis.Redis | None = None
        self._current_trace_id: str | None = None
        self._current_span_id: str | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = RedisClientPool.get(self._redis_url).client
        return self._client

    def start_trace(self, operation: str) -> str:
        trace_id = str(uuid.uuid4())[:16]
        self._current_trace_id = trace_id
        logger.info("Trace started: %s - %s", trace_id, operation)
        return trace_id

    def start_span(
        self,
        span_type: SpanType,
        operation: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if not self._current_trace_id:
            self._current_trace_id = str(uuid.uuid4())[:16]
        span_id = str(uuid.uuid4())[:8]
        self._current_span_id = span_id
        span = TraceSpan(
            span_id=span_id,
            trace_id=self._current_trace_id,
            span_type=span_type.value,
            operation=operation,
            start_time=datetime.now().isoformat(),
            metadata=metadata or {},
        )
        store_span(self.client, span)
        logger.info("Span started: %s (%s)", span_id, span_type.value)
        return span_id

    def end_span(self, span_id: str | None = None, error: str | None = None) -> bool:
        target_span_id = span_id or self._current_span_id
        if not target_span_id or not self._current_trace_id:
            return False
        key = span_key(self._current_trace_id, target_span_id)
        try:
            data = self.client.get(key)
            if data:
                span = json.loads(data)
                span["end_time"] = datetime.now().isoformat()
                span["error"] = error
                self.client.setex(key, TRACE_TTL, json.dumps(span))
                if error:
                    logger.warning("Span %s ended with error: %s", target_span_id, error)
            self._current_span_id = None
            return True
        except Exception as exc:
            logger.error("End span failed: %s", exc, exc_info=True)
            return False

    def get_trace(self, trace_id: str) -> list[dict[str, Any]]:
        return load_trace(self.client, trace_id)

    def format_decision_trail(self, trace_id: str) -> str:
        spans = self.get_trace(trace_id)
        if not spans:
            return f"No trace found: {trace_id}"
        lines = [f"=== Decision Trail: {trace_id} ==="]
        for index, span in enumerate(spans):
            operation = span.get("operation", "")
            start_time = span.get("start_time", "")
            end_time = span.get("end_time", "")
            err = span.get("error", "")
            start = start_time.split("T")[-1][:8] if "T" in start_time else start_time
            end = end_time.split("T")[-1][:8] if end_time and "T" in end_time else "running"
            marker = "X" if err else "O"
            lines.append(
                f"{index + 1}. [{span.get('span_type', '')}] {operation}: {start} - {end} {marker}"
            )
        return "\n".join(lines)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


_redis_tracer: DistributedTracer | None = None


def get_redis_tracer() -> DistributedTracer:
    global _redis_tracer
    if _redis_tracer is None:
        _redis_tracer = DistributedTracer()
    return _redis_tracer


def trace_span(span_type: SpanType, operation: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for automatic Redis span tracing."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_redis_tracer()
            metadata: dict[str, Any] = {"function": func.__name__}
            if args:
                metadata["args"] = str(args)[:100]
            span_id = tracer.start_span(span_type, operation, metadata)
            error: str | None = None
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                error = str(exc)
                raise
            finally:
                tracer.end_span(span_id, error)

        return wrapper

    return decorator
