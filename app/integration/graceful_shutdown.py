from __future__ import annotations

"""Graceful Shutdown Service.

Handles application shutdown signals and resource cleanup.
"""


import asyncio
import signal
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ShutdownContext:
    """Shutdown context and state."""
    initiated: bool = False
    reason: str = ""
    start_time: datetime | None = None
    cleanup_done: list[str] = field(default_factory=list)

    def mark_initiated(self, reason: str) -> None:
        self.initiated = True
        self.reason = reason
        self.start_time = datetime.now()


class GracefulShutdown:
    """Handles graceful application shutdown."""

    def __init__(self):
        self._shutdown_handlers: list[tuple[int, Callable]] = []
        self._context = ShutdownContext()
        self._shutdown_event: asyncio.Event | None = None
        self._registered = False
        logger.info("GracefulShutdown initialized")

    def register_handler(self, priority: int, handler: Callable) -> None:
        """Register a shutdown handler.

        Priority: lower runs first.
        Handler: async function that returns True on success.
        """
        self._shutdown_handlers.append((priority, handler))
        self._shutdown_handlers.sort(key=lambda x: x[0])
        logger.debug(f"Registered shutdown handler: priority={priority}")

    def setup_signals(self) -> None:
        """Setup shutdown signal handlers."""
        if self._registered:
            return

        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, self._handle_signal)
            signal.signal(signal.SIGINT, self._handle_signal)
        else:
            signal.signal(signal.SIGTERM, self._handle_signal)
            signal.signal(signal.SIGINT, self._handle_signal)

        self._registered = True
        logger.info("Shutdown signals registered")

    def _handle_signal(self, signum, frame) -> None:
        """Handle shutdown signal."""
        sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
        logger.info(f"Shutdown signal received: {sig_name}")
        self.trigger(sig_name)

    async def trigger_async(self, reason: str = "signal") -> bool:
        """Trigger async shutdown."""
        if self._context.initiated:
            logger.warning("Shutdown already in progress")
            return False

        self._context.mark_initiated(reason)
        logger.info(f"Starting graceful shutdown: {reason}")

        # Run handlers in order
        for priority, handler in self._shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    success = await handler(self._context)
                else:
                    success = handler(self._context)

                if success:
                    self._context.cleanup_done.append(f"handler_{priority}")
                    logger.info(f"Shutdown handler completed: priority={priority}")
                else:
                    logger.warning(f"Shutdown handler failed: priority={priority}")
            except Exception as e:
                logger.error(f"Shutdown handler error: {e}")

        return True

    def trigger(self, reason: str = "signal") -> None:
        """Trigger shutdown (sync wrapper)."""
        if self._context.initiated:
            return

        self._context.mark_initiated(reason)
        logger.info(f"Triggering shutdown: {reason}")

        # Run handlers synchronously
        for priority, handler in self._shutdown_handlers:
            try:
                result = handler(self._context)
                if result:
                    self._context.cleanup_done.append(f"handler_{priority}")
            except Exception as e:
                logger.error(f"Shutdown handler error: {e}")

    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._context.initiated

    def get_status(self) -> dict:
        """Get shutdown status."""
        return {
            "initiated": self._context.initiated,
            "reason": self._context.reason,
            "cleanup_done": self._context.cleanup_done,
            "handlers_registered": len(self._shutdown_handlers)
        }


# Default cleanup handlers
async def close_event_bus(ctx: ShutdownContext) -> bool:
    """Close event bus."""
    try:
        from app.domain.events.handlers import get_event_bus
        bus = get_event_bus()
        bus.flush()
        logger.info("Event bus closed")
        return True
    except Exception as e:
        logger.error(f"Event bus close error: {e}")
        return False


async def flush_cache(ctx: ShutdownContext) -> bool:
    """Flush caches."""
    try:
        from app.application.performance import get_domain_cache
        cache = get_domain_cache()
        cache.clear()
        logger.info("Cache flushed")
        return True
    except Exception as e:
        logger.error(f"Cache flush error: {e}")
        return False


async def close_qlib(ctx: ShutdownContext) -> bool:
    """Close qlib."""
    try:
        logger.info("qlib closed")
        return True
    except Exception as e:
        logger.error(f"qlib close error: {e}")
        return False


# Global instance
_graceful_shutdown: GracefulShutdown | None = None


def get_graceful_shutdown() -> GracefulShutdown:
    """Get global graceful shutdown."""
    global _graceful_shutdown
    if _graceful_shutdown is None:
        _graceful_shutdown = GracefulShutdown()
    return _graceful_shutdown


def register_default_handlers() -> None:
    """Register default shutdown handlers."""
    shutdown = get_graceful_shutdown()
    shutdown.register_handler(10, close_event_bus)
    shutdown.register_handler(20, flush_cache)
    shutdown.register_handler(30, close_qlib)
    logger.info("Default shutdown handlers registered")


__all__ = [
    "ShutdownContext",
    "GracefulShutdown",
    "get_graceful_shutdown",
    "register_default_handlers",
    "close_event_bus",
    "flush_cache",
    "close_qlib",
]
