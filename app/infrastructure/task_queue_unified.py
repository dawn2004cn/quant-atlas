from __future__ import annotations

"""Unified task queue that delegates to PriorityTaskQueue (threading-based).

Previously this module supported runtime selection between AsyncTaskQueue (asyncio)
and PriorityTaskQueue (threading). PriorityTaskQueue was chosen as the canonical
implementation due to richer feature set (TaskStatus, retries, cancel, queue stats).
"""

from collections.abc import Callable
from typing import Any

from .task_queue_v2 import PriorityTaskQueue as _Impl
from .task_queue_v2 import TaskPriority, TaskStatus


class UnifiedTaskQueue:
    """Delegate to PriorityTaskQueue (threading-based)."""

    def __init__(self, max_workers: int = 4, queue_name: str = "default"):
        self._impl = _Impl(max_workers=max_workers)

    def start(self) -> None:
        self._impl.start()

    def stop(self) -> None:
        self._impl.stop()

    def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        priority: TaskPriority = TaskPriority.MEDIUM,
        **kwargs: Any,
    ) -> str:
        return self._impl.submit(func, *args, priority=priority, **kwargs)

    def submit_with_callback(
        self,
        func: Callable[..., Any],
        callback: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return self._impl.submit_with_callback(func, callback, *args, **kwargs)


# Global instance and accessor
_task_queue: UnifiedTaskQueue | None = None


def get_task_queue() -> UnifiedTaskQueue:
    global _task_queue
    if _task_queue is None:
        _task_queue = UnifiedTaskQueue()
    return _task_queue


def init_task_queue(max_workers: int = 4) -> None:
    global _task_queue
    _task_queue = UnifiedTaskQueue(max_workers=max_workers)


def close_task_queue() -> None:
    global _task_queue
    if _task_queue is not None:
        _task_queue.stop()
        _task_queue = None
