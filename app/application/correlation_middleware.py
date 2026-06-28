from __future__ import annotations

"""Correlation ID Middleware for Flask and Celery.

This module provides middleware that automatically:
- Extracts correlation ID from incoming HTTP headers (X-Correlation-ID)
- Generates new correlation ID for new requests
- Propagates correlation ID to async tasks (Celery)
- Adds correlation ID to all HTTP responses
"""


from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class CorrelationMiddleware:
    """Flask middleware for correlation ID propagation.

    Automatically:
    - Reads X-Correlation-ID from request headers
    - Generates new correlation ID if not provided
    - Sets correlation ID in context for request processing
    - Adds correlation ID to response headers
    """

    def __init__(self, app: Any | None = None):
        self._app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Any) -> None:
        """Initialize middleware with Flask app."""
        self._app = app

        app.before_request(self._before_request)
        app.after_request(self._after_request)

        logger.info("Correlation middleware initialized")

    async def _before_request(self) -> None:
        """Process request before handling."""
        from flask import request

        from .correlation import generate_correlation_id, set_correlation_id

        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = generate_correlation_id()

        set_correlation_id(correlation_id)
        logger.debug(f"Request correlation ID: {correlation_id}")

    async def _after_request(self, response: Any) -> None:
        """Process response after handling."""
        from flask import g

        correlation_id = g.get("correlation_id")
        if correlation_id:
            response.headers["X-Correlation-ID"] = correlation_id

        return response


def init_correlation_middleware(app: Any) -> None:
    """Factory function to initialize correlation middleware."""
    CorrelationMiddleware(app)


class CeleryCorrelationTask:
    """Celery task wrapper that propagates correlation ID.

    Usage:
        from celery import Celery
        from app.application.correlation_middleware import CeleryCorrelationTask

        @CeleryCorrelationTask.task(bind=True)
        def my_task(self, data):
            cid = get_correlation_id()  # Automatically propagated
            log.info(f"Task running with correlation: {cid}")
    """

    @staticmethod
    def propagate_correlation(task_id: str, *args, **kwargs) -> None:
        """Propagate correlation ID to Celery task.

        Should be called in task's before_run or as first operation.
        """
        from .correlation import generate_correlation_id, set_correlation_id

        correlation_id = kwargs.get("_correlation_id")
        if not correlation_id:
            correlation_id = generate_correlation_id()

        set_correlation_id(correlation_id)
        logger.debug(f"Propagated correlation to task {task_id}: {correlation_id}")


class AsyncContextPropagator:
    """Propagates correlation ID through async call boundaries.

    Usage:
        propagator = AsyncContextPropagator()
        await propagator.run_with_context(correlated_function, arg1, arg2)
    """

    @staticmethod
    async def run_with_context(coro, *args, **kwargs):
        """Run coroutine with current correlation ID.

        Args:
            coro: Coroutine to run
            *args, **kwargs: Arguments for coroutine

        Returns:
            Result of coroutine
        """
        from .correlation import get_correlation_id, set_correlation_id

        correlation_id = get_correlation_id()

        async def _run_with_id():
            set_correlation_id(correlation_id)
            return await coro

        return await _run_with_id()


def create_task_with_correlation(coro, *args, **kwargs):
    """Create an async task that propagates correlation ID.

    Usage:
        task = create_task_with_correlation(async_function(), arg1=val)
        result = await task
    """
    import asyncio

    from .correlation import get_correlation_id

    correlation_id = get_correlation_id()
    kwargs["_correlation_id"] = correlation_id

    async def _wrapper():
        from .correlation import set_correlation_id
        set_correlation_id(correlation_id)
        return await coro

    return asyncio.create_task(_wrapper())


__all__ = [
    "CorrelationMiddleware",
    "init_correlation_middleware",
    "CeleryCorrelationTask",
    "AsyncContextPropagator",
    "create_task_with_correlation",
]
