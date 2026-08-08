from __future__ import annotations

from app.infrastructure.realtime.smart_degrade_gateway import (
    SmartDegradeGateway,
    StreamMode,
)


def test_degraded_mode_when_latency_high() -> None:
    gw = SmartDegradeGateway(latency_stream_max_ms=50, latency_batch_max_ms=100)
    gw._probe_redis_latency = lambda: 300.0  # type: ignore[method-assign]
    topo = gw.resolve(["600519", "000001", "999999"])
    assert topo.mode == StreamMode.DEGRADED
    assert "600519" in topo.core_symbols


def test_batch_mode_for_non_core_symbols() -> None:
    gw = SmartDegradeGateway(latency_stream_max_ms=50, latency_batch_max_ms=200)
    gw._probe_redis_latency = lambda: 120.0  # type: ignore[method-assign]
    topo = gw.resolve(["600519", "000001", "999999"])
    assert topo.mode == StreamMode.BATCH
    assert "999999" in topo.batch_symbols


def test_default_thresholds_align_with_slo(monkeypatch) -> None:
    monkeypatch.setenv("QUOTE_LATENCY_SLO_MS", "50")
    monkeypatch.delenv("QUOTE_DEGRADE_STREAM_MS", raising=False)
    monkeypatch.delenv("QUOTE_DEGRADE_BATCH_MS", raising=False)
    gw = SmartDegradeGateway()
    assert gw._stream_max == 80.0  # noqa: SLF001  50 * 1.6
    assert gw._batch_max == 250.0  # noqa: SLF001  50 * 5
