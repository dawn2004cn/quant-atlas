"""
Unified task queue interface that delegates to either AsyncTaskQueue (asyncio) or
PriorityTaskQueue (threading) based on configuration.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from .task_queue import AsyncTaskQueue
from .task_queue_v2 import PriorityTaskQueue


class TaskPriority:
    """Unified task priority enum."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TaskQueueInterface:
    """Abstract interface for task queues."""

    def __init__(self, max_workers: int = 4, queue_name: str = "default"):
        raise NotImplementedError

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def submit(
        self,
        func: Callable[..., Any],
        *args: Any,
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs: Any
    ) -> str:
        """Submit a fire-and-forget task."""
        raise NotImplementedError

    def submit_with_callback(
        self,
        func: Callable[..., Any],
        callback: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> str:
        """Submit a task with completion callback."""
        raise NotImplementedError


class UnifiedTaskQueue(TaskQueueInterface):
    """Delegates to the configured backend (asyncio or threading)."""

    def __init__(self, max_workers: int = 4, queue_name: str = "default"):
        backend = os.getenv("TASK_QUEUE_BACKEND", "asyncio")
        if backend == "threading":
            self._impl = PriorityTaskQueue(max_workers=max_workers)
        else:
            self._impl = AsyncTaskQueue(max_workers=max_workers)

    def start(self) -> None:
        self._impl.start()

    def stop(self) -> None:
        self._impl.stop()

    def submit(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        return self._impl.submit(func, *args, **kwargs)

    def submit_with_callback(
        self, func: Callable[..., Any], callback: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> str:
        return self._impl.submit_with_callback(func, callback, *args, **kwargs)


# Global instance and accessor
_task_queue: UnifiedTaskQueue | None = None

def get_task_queue() -> UnifiedTaskQueue:
    """Get the global unified task queue."""
    global _task_queue
    if _task_queue is None:
        _task_queue = UnifiedTaskQueue()
    return _task_queue

def init_task_queue(max_workers: int = 4) -> None:
    """Initialize the global queue with given workers."""
    global _task_queue
    _task_queue = UnifiedTaskQueue(max_workers=max_workers)

async def close_task_queue() -> None:
    """Close the global queue (async for asyncio backend)."""
    global _task_queue
    if _task_queue is not None:
        await getattr(_task_queue._impl, "close", lambda: None)()
        _task_queue = None
