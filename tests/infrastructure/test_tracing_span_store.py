"""Distributed tracer span store unit tests."""

from app.infrastructure.tracing.span_store import span_key, span_to_dict, trace_list_key
from app.infrastructure.tracing.span_types import SpanType, TraceSpan


def test_span_key_helpers() -> None:
    assert span_key("t1", "s1") == "tracing:spans:t1:s1"
    assert trace_list_key("t1") == "tracing:spans:t1"


def test_span_to_dict_roundtrip_fields() -> None:
    span = TraceSpan(
        span_id="s1",
        trace_id="t1",
        span_type=SpanType.BACKTEST.value,
        operation="run",
        start_time="2026-06-19T10:00:00",
        metadata={"symbol": "600519"},
    )
    data = span_to_dict(span)
    assert data["span_id"] == "s1"
    assert data["metadata"]["symbol"] == "600519"
