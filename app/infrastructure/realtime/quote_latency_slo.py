"""Quote / Redis latency SLO tracker (SRS NFR: push latency target 50ms).

Observability SLO and SmartDegrade thresholds share ``QUOTE_LATENCY_SLO_MS`` as
the base; degrade stream/batch caps are configurable multiples (defaults 1.6x / 5x).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_float

logger = get_logger(__name__)


def resolve_slo_ms() -> float:
    return float(get_runtime_float("QUOTE_LATENCY_SLO_MS", 50.0) or 50.0)


def resolve_degrade_stream_ms(*, slo_ms: float | None = None) -> float:
    base = float(slo_ms if slo_ms is not None else resolve_slo_ms())
    return float(get_runtime_float("QUOTE_DEGRADE_STREAM_MS", base * 1.6) or (base * 1.6))


def resolve_degrade_batch_ms(*, slo_ms: float | None = None) -> float:
    base = float(slo_ms if slo_ms is not None else resolve_slo_ms())
    return float(get_runtime_float("QUOTE_DEGRADE_BATCH_MS", base * 5.0) or (base * 5.0))


def recommend_delivery_mode(latency_ms: float, *, slo_ms: float | None = None) -> str:
    """Map observed latency to stream|batch|degraded using aligned thresholds."""
    stream_max = resolve_degrade_stream_ms(slo_ms=slo_ms)
    batch_max = resolve_degrade_batch_ms(slo_ms=slo_ms)
    if latency_ms >= batch_max:
        return "degraded"
    if latency_ms >= stream_max:
        return "batch"
    return "stream"


class QuoteLatencySloTracker:
    """Rolling-window p50/p95 for quote push latency and Redis ping."""

    def __init__(self, *, slo_ms: float | None = None, window: int = 500) -> None:
        self._slo_ms = float(slo_ms if slo_ms is not None else resolve_slo_ms())
        self._push: deque[float] = deque(maxlen=max(10, window))
        self._redis_pings: deque[float] = deque(maxlen=max(10, window))
        self._last_redis_ping_ms: float | None = None
        self._lock = threading.Lock()

    @property
    def slo_ms(self) -> float:
        return self._slo_ms

    def record_push(self, latency_ms: float) -> None:
        with self._lock:
            self._push.append(float(latency_ms))

    def record_redis_ping(self, latency_ms: float) -> None:
        with self._lock:
            self._last_redis_ping_ms = float(latency_ms)
            self._redis_pings.append(float(latency_ms))

    def _percentile(self, values: list[float], p: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        idx = min(max(int(len(ordered) * p), 0), len(ordered) - 1)
        return round(ordered[idx], 3)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            pushes = list(self._push)
            pings = list(self._redis_pings)
            last_ping = self._last_redis_ping_ms
            slo = self._slo_ms
        p50 = self._percentile(pushes, 0.50)
        p95 = self._percentile(pushes, 0.95)
        avg = round(sum(pushes) / len(pushes), 3) if pushes else None
        # Prefer push p95 for SLO; fall back to redis ping p95 if no push samples.
        score = p95 if p95 is not None else self._percentile(pings, 0.95)
        within = True if score is None else score <= slo
        stream_ms = resolve_degrade_stream_ms(slo_ms=slo)
        batch_ms = resolve_degrade_batch_ms(slo_ms=slo)
        observed = float(score if score is not None else (last_ping or 0.0))
        recommend = recommend_delivery_mode(observed, slo_ms=slo) if score is not None or last_ping is not None else "stream"
        return {
            "slo_ms": slo,
            "degrade_stream_ms": stream_ms,
            "degrade_batch_ms": batch_ms,
            "sample_count": len(pushes),
            "redis_ping_samples": len(pings),
            "avg_ms": avg,
            "p50_ms": p50,
            "p95_ms": p95,
            "last_redis_ping_ms": last_ping,
            "within_slo": within,
            "breached": not within and score is not None,
            "recommend_mode": recommend,
            "actionable": bool(score is not None and score > stream_ms),
            "observed_at": time.time(),
        }

    def probe_and_record_redis(self, redis_url: str | None = None) -> float:
        """Ping Redis once, record latency, return ms (999 on failure)."""
        url = redis_url
        if not url:
            try:
                from app.config import get_settings

                s = get_settings()
                url = getattr(s, "task_message_redis_url", None) or getattr(s, "celery_broker_url", None)
            except Exception:
                url = None
        if not url:
            return 0.0
        try:
            from app.infrastructure.redis_client import RedisClientPool

            client = RedisClientPool.get(url).client
            t0 = time.perf_counter()
            client.ping()
            ms = (time.perf_counter() - t0) * 1000.0
            try:
                client.close()
            except Exception:
                pass
            self.record_redis_ping(ms)
            return ms
        except Exception as exc:
            logger.debug("quote_latency_slo redis probe failed: %s", exc)
            self.record_redis_ping(999.0)
            return 999.0


_tracker: QuoteLatencySloTracker | None = None
_tracker_lock = threading.Lock()


def get_quote_latency_slo() -> QuoteLatencySloTracker:
    global _tracker
    with _tracker_lock:
        if _tracker is None:
            _tracker = QuoteLatencySloTracker()
        return _tracker
