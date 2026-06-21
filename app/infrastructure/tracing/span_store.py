from __future__ import annotations

"""Redis span 存储编解码与 key 命名。"""

import json
from typing import Any

from .span_types import TraceSpan

REDIS_KEY_PREFIX = "tracing:spans:"
MAX_SPANS_PER_TRACE = 100
TRACE_TTL = 3600


def span_key(trace_id: str, span_id: str) -> str:
    return f"{REDIS_KEY_PREFIX}{trace_id}:{span_id}"


def trace_list_key(trace_id: str) -> str:
    return f"{REDIS_KEY_PREFIX}{trace_id}"


def span_to_dict(span: TraceSpan) -> dict[str, Any]:
    return {
        "span_id": span.span_id,
        "trace_id": span.trace_id,
        "span_type": span.span_type,
        "operation": span.operation,
        "start_time": span.start_time,
        "end_time": span.end_time,
        "metadata": span.metadata,
        "error": span.error,
    }


def store_span(client: Any, span: TraceSpan) -> None:
    key = span_key(span.trace_id, span.span_id)
    client.setex(key, TRACE_TTL, json.dumps(span_to_dict(span)))
    list_key = trace_list_key(span.trace_id)
    client.rpush(list_key, span.span_id)
    client.expire(list_key, TRACE_TTL)
    count = client.llen(list_key)
    if count > MAX_SPANS_PER_TRACE:
        oldest = client.lpop(list_key)
        if oldest:
            client.delete(span_key(span.trace_id, oldest.decode() if isinstance(oldest, bytes) else oldest))


def load_trace(client: Any, trace_id: str) -> list[dict[str, Any]]:
    span_ids = client.lrange(trace_list_key(trace_id), 0, -1)
    spans: list[dict[str, Any]] = []
    for raw_id in span_ids:
        span_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id
        data = client.get(span_key(trace_id, span_id))
        if data:
            spans.append(json.loads(data))
    return sorted(spans, key=lambda item: item.get("start_time", ""))
