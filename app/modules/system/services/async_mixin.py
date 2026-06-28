from __future__ import annotations

"""Async service mixin for converting sync services to async."""


import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Any, TypeVar

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

# Shared executor for blocking I/O operations
_io_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="sync_to_async")


def asyncify(func: Callable[..., T]) -> Callable[..., Awaitable[T]]:
    """Decorator to convert sync function to async.

    Usage:
        class MyService:
            @asyncify
            def fetch_data(self, url):
                return requests.get(url).json()

        # Now can be called as: await service.fetch_data(url)
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_io_executor, lambda: func(*args, **kwargs))
    return wrapper


def asyncify_batch(items: list[Any], func: Callable[[Any], Any], max_concurrency: int = 10) -> Awaitable[list[Any]]:
    """Run async function on batch of items with concurrency limit.

    Usage:
        results = await asyncify_batch(
            symbols,
            lambda s: provider.get_quote(s),
            max_concurrency=20
        )
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run_with_semaphore(item):
        async with semaphore:
            return func(item)

    return asyncio.gather(*[_run_with_semaphore(item) for item in items])


class AsyncServiceMixin:
    """Mixin class providing async wrapper for sync service methods.

    Usage:
        class MyService(AsyncServiceMixin):
            def get_quotes(self, codes):
                return self._provider.get_quotes(codes)

            async def get_quotes_async(self, codes):
                return await self._run_async(self.get_quotes, codes)
    """

    def _run_async(self, func: Callable[..., T], *args, **kwargs) -> Awaitable[T]:
        """Run sync function in thread pool."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(_io_executor, lambda: func(*args, **kwargs))

    async def _run_async_with_timeout(
        self,
        func: Callable[..., T],
        timeout: float = 30.0,
        *args,
        **kwargs
    ) -> T:
        """Run sync function with timeout."""
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(_io_executor, lambda: func(*args, **kwargs)),
            timeout=timeout
        )


class BatchAsyncService:
    """Base class for services that need batch async operations."""

    def __init__(self, max_concurrency: int = 20):
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="batch_async")

    async def _batch_process(
        self,
        items: list[Any],
        process_func: Callable[[Any], Any],
        max_concurrent: int = 10
    ) -> list[Any]:
        """Process items concurrently with limit."""
        sem = asyncio.Semaphore(max_concurrent)

        async def _process(item):
            async with sem:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(self._executor, process_func, item)

        return await asyncio.gather(*[_process(item) for item in items])

    def _shutdown(self):
        """Clean up executor."""
        self._executor.shutdown(wait=True)
