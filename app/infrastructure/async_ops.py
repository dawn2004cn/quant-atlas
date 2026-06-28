from __future__ import annotations

"""Async Operations Support.

Background task execution and async repository methods.
"""


import threading
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Task:
    """Background task."""
    id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    submitted_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    result: Any = None
    error: str | None = None


class AsyncTaskQueue:
    """Async task queue with thread pool."""

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._queue: deque[Task] = deque()
        self._running: set[str] = set()
        self._completed: list[Task] = []
        self._max_completed = 100
        self._lock = threading.Lock()
        self._task_id = 0
        logger.info(f"AsyncTaskQueue initialized: workers={max_workers}")

    def submit(self, func: Callable, *args, **kwargs) -> str:
        """Submit a task."""
        self._task_id += 1
        task_id = f"task_{self._task_id}"

        task = Task(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs
        )

        with self._lock:
            self._queue.append(task)
            self._running.add(task_id)

        # Execute async
        self._executor.submit(self._run_task, task)

        logger.debug(f"Task submitted: {task_id}")
        return task_id

    def _run_task(self, task: Task) -> None:
        """Run a task."""
        try:
            task.result = task.func(*task.args, **task.kwargs)
            task.completed_at = datetime.now()
            logger.debug(f"Task completed: {task.id}")
        except Exception as e:
            task.error = str(e)
            task.completed_at = datetime.now()
            logger.error(f"Task failed: {task.id} - {e}")
        finally:
            with self._lock:
                self._running.discard(task.id)
                self._completed.append(task)
                if len(self._completed) > self._max_completed:
                    self._completed.pop(0)

    def get_result(self, task_id: str) -> Any | None:
        """Get task result."""
        with self._lock:
            for task in self._completed:
                if task.id == task_id:
                    if task.error:
                        raise RuntimeError(task.error)
                    return task.result
            return None

    def get_status(self, task_id: str) -> str | None:
        """Get task status."""
        with self._lock:
            if task_id in self._running:
                return "running"
            for task in self._completed:
                if task.id == task_id:
                    return "completed" if not task.error else "failed"
            return "not_found"

    def get_queue_status(self) -> dict:
        """Get queue status."""
        with self._lock:
            return {
                "queued": len(self._queue),
                "running": len(self._running),
                "completed": len(self._completed),
                "total": self._task_id
            }

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown executor."""
        self._executor.shutdown(wait=wait)
        logger.info("AsyncTaskQueue shutdown")


# Global instance
_async_task_queue: AsyncTaskQueue | None = None


def get_async_task_queue() -> AsyncTaskQueue:
    """Get global async task queue."""
    global _async_task_queue
    if _async_task_queue is None:
        _async_task_queue = AsyncTaskQueue(max_workers=4)
    return _async_task_queue


# Decorator for async execution
def run_async(func: Callable) -> Callable:
    """Decorator to run function asynchronously."""
    def async_wrapper(*args, **kwargs):
        queue = get_async_task_queue()
        return queue.submit(func, *args, **kwargs)
    return async_wrapper


__all__ = [
    "Task",
    "AsyncTaskQueue",
    "get_async_task_queue",
    "run_async",
]
