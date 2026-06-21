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
