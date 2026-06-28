"""Process-local task scheduler — lightweight alternative to Celery for simple recurring tasks.

Supports dynamic add/remove at runtime, execution history recording, and thread-safe
scheduling via the ``schedule`` library. Designed for tasks that don't need Celery's
complexity: cache warming, quote polling, periodic cleanup.

Usage:
    from app.core.scheduler import get_scheduler

    sched = get_scheduler()
    sched.add_task("warm-cache", warm_cache, interval=300, unit="seconds", start_immediately=True)
    sched.start()
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from threading import Event, Lock, Thread
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

try:
    import schedule
    _SCHEDULE_AVAILABLE = True
except ImportError:
    _SCHEDULE_AVAILABLE = False


@dataclass
class TaskRecord:
    task_id: str
    task_name: str
    execute_time: datetime
    success: bool
    error: str | None = None
    duration_ms: float = 0.0


class ProcScheduler:
    """Process-local task scheduler (singleton).

    Wraps the ``schedule`` library with thread-safe task management,
    execution history, and graceful shutdown.

    Thread-safety:
        All public methods acquire ``_lock``. The run loop runs in a
        daemon thread and checks ``_stop_flag`` every second.
    """

    _instance: ProcScheduler | None = None
    _initialized: bool = False

    def __new__(cls) -> ProcScheduler:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._available = _SCHEDULE_AVAILABLE
        self._running = False
        self._stop_flag = Event()
        self._thread: Thread | None = None
        self._lock = Lock()
        self._tasks: dict[str, Any] = {}
        self._history: list[TaskRecord] = field(default_factory=list)
        self._max_history = 100
        if not self._available:
            logger.warning("schedule library not installed; ProcScheduler disabled (pip install schedule)")
        self._initialized = True

    # ── Lifecycle ────────────────────────────────────────────────────

    def start(self) -> bool:
        if not self._available:
            return False
        with self._lock:
            if self._running:
                return True
            self._stop_flag.clear()
            self._thread = Thread(target=self._run_loop, daemon=True, name="proc-scheduler")
            self._thread.start()
            self._running = True
            logger.info("ProcScheduler started")
        return True

    def stop(self, timeout: float = 5.0) -> bool:
        if not self._running:
            return True
        self._stop_flag.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout)
        self._running = False
        logger.info("ProcScheduler stopped")
        return True

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Task CRUD ────────────────────────────────────────────────────

    def add_task(
        self,
        task_id: str,
        func: Callable,
        interval: int,
        unit: str = "seconds",
        start_immediately: bool = False,
        **kwargs: Any,
    ) -> bool:
        if not self._available:
            return False
        with self._lock:
            if task_id in self._tasks:
                logger.warning("Task %s already registered", task_id)
                return False

            job = self._build_job(interval, unit)
            if job is None:
                return False

            def wrapper():
                self._execute(task_id, func.__name__, func, **kwargs)

            job.do(wrapper)
            self._tasks[task_id] = job
            logger.info("Scheduled task %s every %d %s", task_id, interval, unit)

            if start_immediately:
                wrapper()
        return True

    def remove_task(self, task_id: str) -> bool:
        if not self._available:
            return False
        with self._lock:
            job = self._tasks.pop(task_id, None)
            if job is None:
                return False
            schedule.cancel_job(job)
            logger.info("Removed task %s", task_id)
        return True

    def list_tasks(self) -> list[str]:
        with self._lock:
            return list(self._tasks.keys())

    def clear(self) -> None:
        if not self._available:
            return
        with self._lock:
            schedule.clear()
            self._tasks.clear()

    # ── History ──────────────────────────────────────────────────────

    def recent_history(self, limit: int = 50) -> list[TaskRecord]:
        with self._lock:
            return self._history[-limit:]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # ── Internals ────────────────────────────────────────────────────

    def _build_job(self, interval: int, unit: str) -> Any | None:
        unit_map = {
            "seconds": schedule.every(interval).seconds,
            "minutes": schedule.every(interval).minutes,
            "hours": schedule.every(interval).hours,
            "days": schedule.every(interval).days,
        }
        builder = unit_map.get(unit)
        if builder is None:
            logger.error("Unsupported time unit: %s", unit)
            return None
        return builder

    def _run_loop(self) -> None:
        while not self._stop_flag.is_set():
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception:
                logger.exception("Scheduler loop error")

    def _execute(self, task_id: str, name: str, func: Callable, **kwargs: Any) -> None:
        start = time.monotonic()
        try:
            func(**kwargs)
            dur = (time.monotonic() - start) * 1000
            self._record(task_id, name, start, True, duration_ms=dur)
        except Exception as exc:
            dur = (time.monotonic() - start) * 1000
            logger.error("Task %s failed: %s", name, exc)
            self._record(task_id, name, start, False, error=str(exc), duration_ms=dur)

    def _record(self, task_id: str, name: str, start: float, ok: bool,
                error: str | None = None, duration_ms: float = 0.0) -> None:
        with self._lock:
            self._history.append(TaskRecord(
                task_id=task_id, task_name=name,
                execute_time=datetime.fromtimestamp(start),
                success=ok, error=error, duration_ms=duration_ms,
            ))
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]


# ── Global accessor ─────────────────────────────────────────────────

_scheduler: ProcScheduler | None = None


def get_scheduler() -> ProcScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ProcScheduler()
    return _scheduler


__all__ = ["ProcScheduler", "TaskRecord", "get_scheduler"]
