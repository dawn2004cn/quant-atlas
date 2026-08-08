"""Quote latency SLO tracker tests (SRS: Redis push ≤50ms target)."""

from app.infrastructure.realtime.quote_latency_slo import (
    QuoteLatencySloTracker,
    get_quote_latency_slo,
    recommend_delivery_mode,
    resolve_degrade_batch_ms,
    resolve_degrade_stream_ms,
)


def test_record_and_snapshot_within_slo():
    t = QuoteLatencySloTracker(slo_ms=50.0, window=100)
    for ms in (10.0, 12.0, 15.0, 20.0):
        t.record_push(ms)
    snap = t.snapshot()
    assert snap["slo_ms"] == 50.0
    assert snap["sample_count"] == 4
    assert snap["p50_ms"] <= 50.0
    assert snap["p95_ms"] <= 50.0
    assert snap["within_slo"] is True
    assert snap["degrade_stream_ms"] == resolve_degrade_stream_ms(slo_ms=50.0)
    assert snap["degrade_batch_ms"] == resolve_degrade_batch_ms(slo_ms=50.0)
    assert snap["recommend_mode"] == "stream"
    assert snap["actionable"] is False


def test_breaches_slo_when_p95_high():
    t = QuoteLatencySloTracker(slo_ms=50.0, window=100)
    for ms in (10.0, 20.0, 30.0, 40.0, 200.0):
        t.record_push(ms)
    snap = t.snapshot()
    assert snap["within_slo"] is False
    assert snap["p95_ms"] >= 50.0
    assert snap["breached"] is True
    assert snap["recommend_mode"] in {"batch", "degraded"}
    assert snap["actionable"] is True


def test_record_redis_ping():
    t = QuoteLatencySloTracker(slo_ms=50.0)
    t.record_redis_ping(8.5)
    snap = t.snapshot()
    assert snap["last_redis_ping_ms"] == 8.5


def test_recommend_delivery_mode_aligned():
    assert recommend_delivery_mode(10.0, slo_ms=50.0) == "stream"
    assert recommend_delivery_mode(90.0, slo_ms=50.0) == "batch"
    assert recommend_delivery_mode(300.0, slo_ms=50.0) == "degraded"


def test_singleton_get():
    a = get_quote_latency_slo()
    b = get_quote_latency_slo()
    assert a is b
