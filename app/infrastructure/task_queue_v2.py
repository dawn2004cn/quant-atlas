from __future__ import annotations

"""Task queue with priority support."""


import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import PriorityQueue
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    HIGH = 1    # Real-time trading signals
    MEDIUM = 2  # Daily data updates
    LOW = 3     # Background factor mining


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING

    func: Callable | None = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)

    result: Any = None
    error: str | None = None

    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    retries: int = 0
    max_retries: int = 3

    def __lt__(self, other: Task):
        """Compare tasks by priority."""
        return self.priority.value < other.priority.value


class PriorityTaskQueue:
    """Task queue with priority support."""

    def __init__(self, max_workers: int = 4):
        self._queue: PriorityQueue = PriorityQueue()
        self._tasks: dict[str, Task] = {}
        self._workers: list[threading.Thread] = []
        self._max_workers = max_workers
        self._running = False
        logger.info(f"PriorityTaskQueue initialized with {max_workers} workers")

    def start(self):
        """Start the task queue workers."""
        if self._running:
            return

        self._running = True

        for _i in range(self._max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self._workers.append(worker)

        logger.info(f"Started {self._max_workers} task queue workers")

    def stop(self, timeout: float = 5.0):
        """Stop the task queue workers."""
        self._running = False

        for worker in self._workers:
            worker.join(timeout=timeout)

        self._workers.clear()
        logger.info("Task queue workers stopped")

    def submit(
        self,
        func: Callable,
        *args,
        name: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        **kwargs
    ) -> str:
        """Submit a task to the queue."""
        task = Task(
            name=name or func.__name__,
            priority=priority,
            func=func,
            args=args,
            kwargs=kwargs,
        )

        self._tasks[task.id] = task
        self._queue.put(task)

        logger.info(f"Task submitted: {task.id} ({task.name}) priority={priority.name}")
        return task.id

    def submit_delayed(
        self,
        delay_seconds: float,
        func: Callable,
        *args,
        **kwargs
    ) -> str:
        """Submit a delayed task."""
        import time

        def delayed_func():
            time.sleep(delay_seconds)
            return func(*args, **kwargs)

        return self.submit(
            delayed_func,
            name=f"delayed_{func.__name__}",
            priority=TaskPriority.LOW,
        )

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                logger.info(f"Task cancelled: {task_id}")
                return True
        return False

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Get all tasks with specific status."""
        return [t for t in self._tasks.values() if t.status == status]

    def get_queue_stats(self) -> dict:
        """Get queue statistics."""
        stats = {
            "pending": len(self.get_tasks_by_status(TaskStatus.PENDING)),
            "running": len(self.get_tasks_by_status(TaskStatus.RUNNING)),
            "completed": len(self.get_tasks_by_status(TaskStatus.COMPLETED)),
            "failed": len(self.get_tasks_by_status(TaskStatus.FAILED)),
            "total": len(self._tasks),
        }
        return stats

    def _worker(self):
        """Worker thread that processes tasks."""
        while self._running:
            try:
                task = self._queue.get(timeout=1)

                if task.status == TaskStatus.CANCELLED:
                    continue

                self._execute_task(task)

            except Exception:
                continue

    def _execute_task(self, task: Task):
        """Execute a task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        logger.info(f"Task started: {task.id} ({task.name})")

        try:
            if task.func:
                task.result = task.func(*task.args, **task.kwargs)
            task.status = TaskStatus.COMPLETED

        except Exception as e:
            logger.error(f"Task failed: {task.id} - {e}")
            task.error = str(e)

            if task.retries < task.max_retries:
                task.retries += 1
                task.status = TaskStatus.PENDING
                self._queue.put(task)
                logger.info(f"Task retry {task.retries}/{task.max_retries}: {task.id}")
            else:
                task.status = TaskStatus.FAILED

        finally:
            task.completed_at = datetime.now()

            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                logger.info(
                    f"Task {task.status.value}: {task.id} "
                    f"in {(task.completed_at - task.started_at).total_seconds():.2f}s"
                )


_task_queue: PriorityTaskQueue | None = None


def get_task_queue() -> PriorityTaskQueue:
    """Get the global task queue."""
    global _task_queue
    if _task_queue is None:
        _task_queue = PriorityTaskQueue()
        _task_queue.start()
    return _task_queue


def submit_task(
    func: Callable,
    *args,
    priority: TaskPriority = TaskPriority.MEDIUM,
    **kwargs
) -> str:
    """Submit a task to the global queue."""
    return get_task_queue().submit(func, *args, priority=priority, **kwargs)


__all__ = [
    "TaskPriority",
    "TaskStatus",
    "Task",
    "PriorityTaskQueue",
    "get_task_queue",
    "submit_task",
]
