from __future__ import annotations

"""Smart Degrade Gateway adapt quote delivery mode from SystemPulse / Redis latency."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime, get_runtime_int

logger = get_logger(__name__)


class StreamMode(str, Enum):
    STREAM = "stream"
    BATCH = "batch"
    DEGRADED = "degraded"


@dataclass
class StreamTopology:
    """Resolved delivery topology for realtime quotes."""

    mode: StreamMode = StreamMode.STREAM
    redis_latency_ms: float = 0.0
    core_symbols: list[str] = field(default_factory=list)
    batch_symbols: list[str] = field(default_factory=list)
    stream_interval_sec: int = 5
    batch_interval_sec: int = 30
    reason: str = ""


class SmartDegradeGateway:
    """Choose stream vs batch per symbol based on infra health."""

    def __init__(
        self,
        *,
        redis_url: str | None = None,
        latency_stream_max_ms: float = 80.0,
        latency_batch_max_ms: float = 250.0,
    ) -> None:
        self._redis_url = redis_url
        self._stream_max = latency_stream_max_ms
        self._batch_max = latency_batch_max_ms
        self._topology = StreamTopology()
        self._last_probe = 0.0
        self._tick = 0

    @property
    def topology(self) -> StreamTopology:
        return self._topology

    def core_symbols(self) -> list[str]:
        raw = (get_runtime("WS_QUOTE_SYMBOLS", "") or "").strip()
        if raw:
            return [s.strip().upper() for s in raw.split(",") if s.strip()][:20]
        return ["600519", "000001", "000858", "601318", "300750"]

    def resolve(
        self,
        all_symbols: list[str],
        *,
        pulse_ctx: Any | None = None,
    ) -> StreamTopology:
        """Probe Redis and pick delivery mode."""
        latency = self._probe_redis_latency()
        mode, reason = self._pick_mode(latency, pulse_ctx)
        core = self.core_symbols()
        core_set = {s.upper() for s in core}
        all_upper = [s.upper() for s in all_symbols if s]
        batch = [s for s in all_upper if s not in core_set]

        if mode == StreamMode.DEGRADED:
            batch = all_upper
            core = core[:3]

        base_iv = max(1, get_runtime_int("WS_QUOTE_INTERVAL_SEC", 5))
        self._topology = StreamTopology(
            mode=mode,
            redis_latency_ms=round(latency, 2),
            core_symbols=core,
            batch_symbols=batch if mode != StreamMode.STREAM else [],
            stream_interval_sec=base_iv,
            batch_interval_sec=max(20, base_iv * 4),
            reason=reason,
        )
        return self._topology

    def should_stream_now(self, symbol: str) -> bool:
        sym = symbol.strip().upper()
        if self._topology.mode == StreamMode.STREAM:
            return True
        return sym in {s.upper() for s in self._topology.core_symbols}

    def should_batch_now(self) -> bool:
        self._tick += 1
        if self._topology.mode == StreamMode.STREAM:
            return False
        every = max(1, self._topology.batch_interval_sec // self._topology.stream_interval_sec)
        return self._tick % every == 0

    def batch_symbol_list(self, all_symbols: list[str]) -> list[str]:
        if self._topology.mode == StreamMode.STREAM:
            return []
        core_set = {s.upper() for s in self._topology.core_symbols}
        return [s.upper() for s in all_symbols if s.upper() not in core_set]

    def _probe_redis_latency(self) -> float:
        now = time.time()
        if now - self._last_probe < 10 and self._topology.redis_latency_ms > 0:
            return self._topology.redis_latency_ms
        self._last_probe = now

        url = self._redis_url
        if not url:
            try:
                from app.config import get_settings
                s = get_settings()
                url = getattr(s, "task_message_redis_url", None) or getattr(
                    s, "celery_broker_url", None
                )
            except Exception:
                url = None
        if not url:
            return 0.0
        try:
            from app.infrastructure.redis_client import RedisClientPool
            client = RedisClientPool.get(url).client
            t0 = time.perf_counter()
            client.ping()
            ms = (time.perf_counter() - t0) * 1000
            client.close()
            return ms
        except Exception as exc:
            logger.debug("redis latency probe failed: %s", exc)
            return 999.0

    def _pick_mode(self, latency_ms: float, pulse_ctx: Any | None) -> tuple[StreamMode, str]:
        redis_status = "ok"
        if pulse_ctx is not None:
            try:
                from app.modules.system.services.system.system_pulse_service import (
                    SystemPulseService,
                )
                pulse = SystemPulseService().build_pulse(pulse_ctx)
                for comp in pulse.components:
                    if comp.id == "redis" and comp.status != "ok":
                        redis_status = comp.status
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass

        if latency_ms >= self._batch_max or redis_status == "degraded":
            return StreamMode.DEGRADED, f"redis_latency={latency_ms:.0f}ms_or_status={redis_status}"
        if latency_ms >= self._stream_max:
            return StreamMode.BATCH, f"redis_latency={latency_ms:.0f}ms"
        return StreamMode.STREAM, "healthy"


_gateway: SmartDegradeGateway | None = None


def get_smart_degrade_gateway() -> SmartDegradeGateway:
    global _gateway
    if _gateway is None:
        _gateway = SmartDegradeGateway()
    return _gateway
