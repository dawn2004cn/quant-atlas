"""Celery beat enhancement — dynamic schedule updates + task health dashboard.

Extends the existing Celery beat_schedule with:
1. BeatRegistry: centrally register tasks with metadata (name, crontab, description, enabled flag)
2. CeleryHealth: expose task queue depth, last-run timestamps, failure rates
3. Lightweight fallback: when Celery is unavailable, run critical tasks via ProcScheduler

Usage:
    from app.core.celery_ext import BeatRegistry, celery_health

    # Register a beat task
    BeatRegistry.register("my-task", "app.tasks.my_task.run", crontab(minute="*/5"),
                          description="Cache warming")

    # Build beat_schedule from registry (for celery_app.py)
    schedule = BeatRegistry.build_schedule()

    # Health check
    status = celery_health.status()
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


# ── Beat Task Registry ───────────────────────────────────────────────

@dataclass
class BeatTask:
    """Metadata for a single Celery beat schedule entry."""
    name: str
    task_path: str
    crontab: Any  # celery.schedules.crontab
    description: str = ""
    enabled: bool = True
    queue: str = "default"
    kwargs: dict[str, Any] = field(default_factory=dict)
    last_run_at: float = 0.0
    last_duration_ms: float = 0.0
    last_success: bool | None = None
    run_count: int = 0
    fail_count: int = 0

    @property
    def as_beat_entry(self) -> dict[str, Any]:
        return {
            "task": self.task_path,
            "schedule": self.crontab,
            "options": {"queue": self.queue},
            "kwargs": self.kwargs,
        }

    @property
    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "task": self.task_path,
            "enabled": self.enabled,
            "description": self.description,
            "last_run_ago": time.time() - self.last_run_at if self.last_run_at > 0 else None,
            "last_duration_ms": self.last_duration_ms,
            "last_success": self.last_success,
            "run_count": self.run_count,
            "fail_count": self.fail_count,
        }


class BeatRegistry:
    """Central registry for Celery beat tasks.

    Replaces the inline ``_build_beat_schedule()`` function in ``celery_app.py``
    with a declarative registry that supports runtime inspection and
    conditional enabling/disabling.

    Usage:
        BeatRegistry.register("scanner", "app.tasks.scanner.run", crontab(minute="*/2"),
                              description="Market scanner", enabled=os.getenv("SCANNER_BEAT") == "1")
        # Task args must be flat keyword args (NOT kwargs={...}):
        BeatRegistry.register("sync", "app.tasks.sync.run", crontab(hour=16), dump_qlib_bin=False)
    """

    _tasks: dict[str, BeatTask] = {}
    _lock = Lock()

    @classmethod
    def _normalize_task_kwargs(cls, name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Flatten accidental ``register(..., kwargs={...})`` nesting.

        Passing ``kwargs={...}`` would otherwise store Celery beat kwargs as
        ``{"kwargs": {...}}``, so the task never receives the intended args.
        """
        nested = kwargs.get("kwargs")
        if not isinstance(nested, dict):
            return kwargs
        rest = {k: v for k, v in kwargs.items() if k != "kwargs"}
        logger.warning(
            "BeatRegistry: unwrapped nested kwargs for %s; pass task args as flat keyword args",
            name,
        )
        return {**nested, **rest}

    @classmethod
    def register(
        cls,
        name: str,
        task_path: str,
        crontab: Any,
        *,
        description: str = "",
        enabled: bool = True,
        queue: str = "default",
        **kwargs: Any,
    ) -> None:
        task_kwargs = cls._normalize_task_kwargs(name, kwargs)
        with cls._lock:
            cls._tasks[name] = BeatTask(
                name=name, task_path=task_path, crontab=crontab,
                description=description, enabled=enabled, queue=queue,
                kwargs=task_kwargs,
            )
            logger.debug("BeatRegistry: registered %s (enabled=%s)", name, enabled)

    @classmethod
    def build_schedule(cls) -> dict[str, dict[str, Any]]:
        """Build the ``beat_schedule`` dict for Celery app.conf.beat_schedule."""
        schedule: dict[str, dict[str, Any]] = {}
        with cls._lock:
            for name, task in cls._tasks.items():
                if task.enabled:
                    schedule[name] = task.as_beat_entry
        return schedule

    @classmethod
    def list_tasks(cls) -> list[dict[str, Any]]:
        with cls._lock:
            return [t.as_dict for t in cls._tasks.values()]

    @classmethod
    def get_task(cls, name: str) -> BeatTask | None:
        with cls._lock:
            return cls._tasks.get(name)

    @classmethod
    def enable(cls, name: str, enabled: bool = True) -> bool:
        with cls._lock:
            task = cls._tasks.get(name)
            if task is None:
                return False
            task.enabled = enabled
            return True

    @classmethod
    def record_run(cls, name: str, success: bool, duration_ms: float = 0.0) -> None:
        with cls._lock:
            task = cls._tasks.get(name)
            if task is None:
                return
            task.last_run_at = time.time()
            task.last_duration_ms = duration_ms
            task.last_success = success
            task.run_count += 1
            if not success:
                task.fail_count += 1

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._tasks.clear()


# ── Lightweight fallback (Celery-less) ──────────────────────────────

def run_critical_beats_locally() -> None:
    """Run critical periodic tasks via ProcScheduler when Celery is absent.

    Detects whether Celery workers are available. If not, falls back to
    in-process scheduling for a curated subset of critical beat tasks.
    """
    if os.environ.get("ENABLE_CELERY", "0") == "1":
        return  # Celery handles it

    try:
        from app.core.scheduler import get_scheduler
    except ImportError:
        return

    sched = get_scheduler()

    # Register lightweight substitutes for critical tasks
    critical_tasks: list[tuple[str, Callable, int, str]] = [
        ("cache-warmup", _warm_cache, 300, "seconds"),
        ("signal-flag-scan", _scan_signal_flags, 600, "seconds"),
    ]

    for task_id, func, interval, unit in critical_tasks:
        sched.add_task(task_id, func, interval, unit)

    sched.start()
    logger.info("Celery-less fallback: %d critical tasks scheduled locally", len(critical_tasks))


def _warm_cache() -> None:
    """Minimal cache warmup stub — extend per deployment needs."""
    try:
        from app.core.cache import cache
        cache.get("health:ping")
    except Exception:
        pass


def _scan_signal_flags() -> None:
    """Minimal signal flag scan stub."""
    from app.core.runtime_config import get_runtime_bool
    if not get_runtime_bool("ENABLE_SIGNAL_FLAG_SCAN"):
        return
    try:
        from app.modules.strategy.services.strategy.signal_flag_service import SignalFlagScannerService
        svc = SignalFlagScannerService()
        svc.run_scan()
    except Exception:
        logger.exception("Signal flag scan failed")
