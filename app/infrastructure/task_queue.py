from __future__ import annotations

"""Async task queue for heavy computations (Rust indicators, ML models, etc.)."""


import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class TaskPriority(Enum):
    HIGH = 3
    NORMAL = 2
    LOW = 1


@dataclass
class AsyncTask:
    """Represents a task in the async queue."""
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    created_at: datetime
    callback: Callable | None = None


class AsyncTaskQueue:
    """Async task queue with priority support for heavy computations.

    Usage:
        queue = AsyncTaskQueue(max_workers=4)

        # Submit heavy computation
        task_id = await queue.submit(
            compute_indicators,
            args=(symbols,),
            priority=TaskPriority.NORMAL
        )

        # Get result
        result = await queue.get_result(task_id)
    """

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="async_task"
        )
        self._tasks: dict[str, asyncio.Future] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = True
        self._worker_task: asyncio.Task | None = None

    async def start(self):
        """Start the task queue workers."""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("AsyncTaskQueue started with %d workers", self._max_workers)

    async def stop(self):
        """Stop the task queue and wait for pending tasks."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError as e:
                logger.warning("task_queue.py.stop: %s", e)
        self._executor.shutdown(wait=True)
        logger.info("AsyncTaskQueue stopped")

    async def submit(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Submit a task to the queue."""
        import uuid
        task_id = str(uuid.uuid4())[:8]

        kwargs = kwargs or {}
        future = asyncio.loop.run_in_executor(
            self._executor,
            lambda: func(*args, **kwargs)
        )

        self._tasks[task_id] = future
        logger.debug("Task %s submitted with priority %s", task_id, priority.name)
        return task_id

    async def submit_with_callback(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        on_complete: Callable[[Any], None] = None,
    ) -> str:
        """Submit a task with callback when complete."""
        import uuid
        task_id = str(uuid.uuid4())[:8]

        kwargs = kwargs or {}

        async def _run_with_callback():
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                lambda: func(*args, **kwargs)
            )
            if on_complete:
                try:
                    on_complete(result)
                except Exception as e:
                    logger.warning("Task callback failed: %s", e)
            return result

        future = asyncio.create_task(_run_with_callback())
        self._tasks[task_id] = future
        return task_id

    async def get_result(self, task_id: str, timeout: float = 60.0) -> Any:
        """Get the result of a submitted task."""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")

        future = self._tasks[task_id]
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task {task_id} timed out after {timeout}s") from None
        finally:
            self._tasks.pop(task_id, None)

    async def _worker(self):
        """Worker coroutine to process queue."""
        while self._running:
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break


# Global task queue instance
_global_queue: AsyncTaskQueue | None = None


def get_task_queue() -> AsyncTaskQueue:
    """Get the global async task queue instance."""
    global _global_queue
    if _global_queue is None:
        _global_queue = AsyncTaskQueue(max_workers=4)
    return _global_queue


async def init_task_queue():
    """Initialize the global task queue."""
    queue = get_task_queue()
    await queue.start()


async def close_task_queue():
    """Close the global task queue."""
    global _global_queue
    if _global_queue:
        await _global_queue.stop()
        _global_queue = None


# Convenience functions
async def submit_heavy_task(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    priority: TaskPriority = TaskPriority.NORMAL,
) -> str:
    """Submit a heavy computation task to the global queue."""
    return await get_task_queue().submit(func, args, kwargs, priority)


async def compute_in_background(
    func: Callable,
    *args,
    priority: TaskPriority = TaskPriority.NORMAL,
    **kwargs
) -> Awaitable[Any]:
    """Decorator/utility to run computation in background."""
    task_id = await submit_heavy_task(func, args, kwargs, priority)
    return get_task_queue().get_result(task_id)
