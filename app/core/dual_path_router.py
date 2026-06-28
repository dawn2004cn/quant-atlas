"""Dual-Path Architecture — Fast/Slow Path separation.
Fast Path: execution + risk management, microsecond-grade via GlobalStateBus.
Slow Path: AI cognition (MetaArbiter, MemoryFabric, PromptEvolution), second-grade async observer."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any

from app.core.logger import get_logger
from app.core.mesh.global_state_bus import get_global_state_bus

logger = get_logger(__name__)


class PathType(Enum):
    FAST = auto()   # execution + risk — ms级, no AI
    SLOW = auto()   # AI cognition — s级, async observer


class PathPriority(Enum):
    CRITICAL = auto()  # stop-loss, position limit — always first
    HIGH = auto()      # order execution
    NORMAL = auto()    # pre-trade validation
    LOW = auto()       # AI analysis, backtest


@dataclass
class PathTask:
    """A task routed to either Fast or Slow path."""
    task_id: str
    path: PathType
    priority: PathPriority
    handler: str  # service method name
    payload: dict
    max_latency_ms: int  # SLA
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    error: str = ""


@dataclass
class PathMetrics:
    """Latency and throughput metrics per path."""
    path: PathType
    total_tasks: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_count: int = 0
    last_updated: str = ""


class DualPathRouter:
    """Routes tasks to Fast or Slow path based on type and priority.

    Fast Path (execution/risk):
    - Direct call via GlobalStateBus
    - No AI inference in the loop
    - Target: < 10ms for stop-loss, < 100ms for order execution

    Slow Path (cognition):
    - Async observer pattern
    - AI analysis, strategy suggestions, parameter tuning
    - Target: < 5s for most operations
    """

    def __init__(self):
        self._bus = get_global_state_bus()
        self._lock = threading.Lock()
        self._fast_handlers: dict[str, Callable] = {}
        self._slow_handlers: dict[str, Callable] = {}
        self._metrics: dict[PathType, PathMetrics] = {
            PathType.FAST: PathMetrics(path=PathType.FAST),
            PathType.SLOW: PathMetrics(path=PathType.SLOW),
        }
        self._latency_buffer: dict[PathType, list[float]] = {
            PathType.FAST: [],
            PathType.SLOW: [],
        }
        self._running = False

    def register_fast_handler(self, name: str, handler: Callable):
        """Register a Fast Path handler (execution/risk — no AI)."""
        with self._lock:
            self._fast_handlers[name] = handler
        logger.info("Fast Path handler registered: %s", name)

    def register_slow_handler(self, name: str, handler: Callable):
        """Register a Slow Path handler (AI cognition — async)."""
        with self._lock:
            self._slow_handlers[name] = handler
        logger.info("Slow Path handler registered: %s", name)

    def route_fast(self, task: PathTask) -> dict:
        """Execute a task on the Fast Path — synchronous, microsecond-grade."""
        start = time.perf_counter()
        try:
            handler = self._fast_handlers.get(task.handler)
            if not handler:
                raise ValueError(f"Fast Path handler not found: {task.handler}")

            # Write to GlobalStateBus for cross-process visibility
            self._bus.write_state(f"fast_path.{task.task_id}", {
                "task_id": task.task_id,
                "handler": task.handler,
                "status": "executing",
                "priority": task.priority.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            result = handler(task.payload)

            # Update state
            self._bus.write_state(f"fast_path.{task.task_id}", {
                "status": "completed",
                "result": str(result)[:200],
            })

            elapsed_ms = (time.perf_counter() - start) * 1000
            self._record_latency(PathType.FAST, elapsed_ms)
            return {"ok": True, "result": result, "latency_ms": round(elapsed_ms, 3)}

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._record_error(PathType.FAST)
            logger.error("Fast Path task %s failed: %s (%dms)", task.task_id, exc, elapsed_ms)
            return {"ok": False, "error": str(exc), "latency_ms": round(elapsed_ms, 3)}

    def route_slow(self, task: PathTask) -> dict:
        """Execute a task on the Slow Path — async observer pattern."""
        start = time.perf_counter()
        try:
            handler = self._slow_handlers.get(task.handler)
            if not handler:
                raise ValueError(f"Slow Path handler not found: {task.handler}")

            # Slow Path runs in a thread to avoid blocking Fast Path
            def _run():
                try:
                    handler(task.payload)
                except Exception as exc:
                    logger.warning("Slow Path task %s failed: %s", task.task_id, exc)

            thread = threading.Thread(target=_run, daemon=True)
            thread.start()

            elapsed_ms = (time.perf_counter() - start) * 1000
            self._record_latency(PathType.SLOW, elapsed_ms)
            return {"ok": True, "dispatched": True, "latency_ms": round(elapsed_ms, 3)}

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._record_error(PathType.SLOW)
            return {"ok": False, "error": str(exc), "latency_ms": round(elapsed_ms, 3)}

    def get_metrics(self) -> dict[str, Any]:
        """Get latency metrics for both paths."""
        with self._lock:
            return {
                "fast_path": {
                    "total_tasks": self._metrics[PathType.FAST].total_tasks,
                    "avg_latency_ms": round(self._metrics[PathType.FAST].avg_latency_ms, 3),
                    "p95_latency_ms": round(self._metrics[PathType.FAST].p95_latency_ms, 3),
                    "error_count": self._metrics[PathType.FAST].error_count,
                },
                "slow_path": {
                    "total_tasks": self._metrics[PathType.SLOW].total_tasks,
                    "avg_latency_ms": round(self._metrics[PathType.SLOW].avg_latency_ms, 3),
                    "p95_latency_ms": round(self._metrics[PathType.SLOW].p95_latency_ms, 3),
                    "error_count": self._metrics[PathType.SLOW].error_count,
                },
            }

    def _record_latency(self, path: PathType, latency_ms: float):
        with self._lock:
            buf = self._latency_buffer[path]
            buf.append(latency_ms)
            if len(buf) > 100:
                buf.pop(0)
            metrics = self._metrics[path]
            metrics.total_tasks += 1
            metrics.avg_latency_ms = sum(buf) / len(buf)
            sorted_buf = sorted(buf)
            p95_idx = int(len(sorted_buf) * 0.95)
            metrics.p95_latency_ms = sorted_buf[p95_idx] if p95_idx < len(sorted_buf) else 0
            metrics.last_updated = datetime.now(timezone.utc).isoformat()

    def _record_error(self, path: PathType):
        with self._lock:
            self._metrics[path].error_count += 1


# Global singleton
_router: DualPathRouter | None = None


def get_dual_path_router() -> DualPathRouter:
    global _router
    if _router is None:
        _router = DualPathRouter()
    return _router
