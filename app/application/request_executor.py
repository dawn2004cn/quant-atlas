"""Run async coroutines from synchronous Flask/WSGI handlers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Dedicated pool when a loop is already running (e.g. nested calls, some test runners).
_async_runner_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="request_async")


def run_async(
    coro: Coroutine[object, object, T] | Callable[[], Awaitable[T]],
) -> T:
    """Execute a coroutine from a sync route or service boundary.

    Prefer this over ad-hoc ``asyncio.get_event_loop()`` / ``run_until_complete`` in
    presentation routes. Uses ``asyncio.run`` when no loop is running; otherwise
    runs the coroutine in a worker thread.
    """
    if callable(coro) and not asyncio.iscoroutine(coro):
        awaitable = coro()
    else:
        awaitable = coro

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    logger.debug("run_async: delegating to thread pool (loop already running)")
    future = _async_runner_pool.submit(asyncio.run, awaitable)
    return future.result()
