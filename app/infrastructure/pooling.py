from __future__ import annotations

"""Connection Pooling Infrastructure.

Provides connection pooling for database and cache resources.
"""


import threading
import time
from collections import deque
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class PoolConfig:
    """Connection pool configuration."""
    max_size: int = 10
    min_size: int = 2
    max_idle_time: float = 300.0
    checkout_timeout: float = 30.0
    recycle_time: float = 3600.0


@dataclass
class PoolStats:
    """Pool statistics."""
    active: int = 0
    idle: int = 0
    total: int = 0
    waiters: int = 0
    checkouts: int = 0
    checkins: int = 0
    timeouts: int = 0


class PooledConnection(Generic[T]):
    """A pooled connection wrapper."""

    def __init__(self, conn: T, pool: ConnectionPool[T], created_at: float):
        self._conn = conn
        self._pool = pool
        self._created_at = created_at
        self._checked_out_at: float | None = None
        self._in_use = False

    @property
    def connection(self) -> T:
        return self._conn

    @property
    def age(self) -> float:
        return time.time() - self._created_at

    def is_stale(self, recycle_time: float) -> bool:
        return self.age > recycle_time

    def release(self) -> None:
        if self._in_use:
            self._in_use = False
            self._checked_out_at = None
            self._pool._return_connection(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


class ConnectionPool(Generic[T]):
    """Generic connection pool."""

    def __init__(
        self,
        factory: Callable[[], T],
        config: PoolConfig = None
    ):
        self._factory = factory
        self._config = config or PoolConfig()
        self._idle: deque[PooledConnection[T]] = deque()
        self._active: set[PooledConnection[T]] = set()
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._stats = PoolStats()
        self._closed = False
        self._stats_lock = threading.Lock()

        logger.info(f"ConnectionPool initialized: max={self._config.max_size}")

    def initialize(self) -> None:
        """Initialize pool with minimum connections."""
        with self._lock:
            for _ in range(self._config.min_size):
                conn = self._create()
                self._idle.append(conn)
                self._stats.idle += 1
                self._stats.total += 1

        logger.info(f"Pool initialized: {self._config.min_size} connections")

    def _create(self) -> PooledConnection[T]:
        """Create a new connection."""
        conn = self._factory()
        return PooledConnection(conn, self, time.time())

    @contextmanager
    def checkout(self, timeout: float = None):
        """Checkout a connection from the pool."""
        if self._closed:
            raise RuntimeError("Pool is closed")

        timeout = timeout or self._config.checkout_timeout
        deadline = time.time() + timeout

        with self._lock:
            # Try to get from idle
            while self._idle:
                pooled = self._idle.pop()
                # Check if stale
                if pooled.is_stale(self._config.recycle_time):
                    logger.debug("Connection stale, recreating")
                    continue
                break
            else:
                # No idle connections, try to create new
                if self._stats.total < self._config.max_size:
                    pooled = self._create()
                    self._stats.total += 1
                else:
                    # Wait for available connection
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        with self._stats_lock:
                            self._stats.timeouts += 1
                        raise TimeoutError("Connection pool exhausted")

                    self._stats.waiters += 1
                    try:
                        self._cond.wait(remaining)
                    finally:
                        self._stats.waiters -= 1

                    if self._idle:
                        pooled = self._idle.pop()
                    else:
                        with self._stats_lock:
                            self._stats.timeouts += 1
                        raise TimeoutError("Connection pool timeout")

            pooled._in_use = True
            pooled._checked_out_at = time.time()
            self._active.add(pooled)
            self._stats.active += 1
            self._stats.idle = max(0, self._stats.idle - 1)

            with self._stats_lock:
                self._stats.checkouts += 1

        try:
            yield pooled
        finally:
            self._return_connection(pooled)

    def _return_connection(self, pooled: PooledConnection[T]) -> None:
        """Return a connection to the pool."""
        with self._lock:
            self._active.discard(pooled)
            self._stats.active = max(0, self._stats.active - 1)

            if self._closed or pooled.is_stale(self._config.recycle_time):
                self._stats.total -= 1
                logger.debug("Connection closed (stale or pool closed)")
                return

            self._idle.append(pooled)
            self._stats.idle += 1

            with self._stats_lock:
                self._stats.checkins += 1

            self._cond.notify()

    def close_idle(self) -> int:
        """Close idle connections beyond min_size."""
        with self._lock:
            closed = 0
            while len(self._idle) > self._config.min_size:
                self._idle.pop()
                self._stats.total -= 1
                self._stats.idle -= 1
                closed += 1

            if closed:
                logger.info(f"Closed {closed} idle connections")

            return closed

    def close(self) -> None:
        """Close all connections."""
        with self._lock:
            self._closed = True

            while self._idle:
                self._idle.pop()
                self._stats.total -= 1

            self._stats.idle = 0
            self._stats.active = 0

            logger.info("Pool closed")

    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        with self._stats_lock:
            return PoolStats(
                active=self._stats.active,
                idle=len(self._idle),
                total=self._stats.total,
                waiters=self._stats.waiters,
                checkouts=self._stats.checkouts,
                checkins=self._stats.checkins,
                timeouts=self._stats.timeouts
            )


# Global pools
_db_pool: ConnectionPool[Any] | None = None
_cache_pool: ConnectionPool[Any] | None = None


def get_db_pool() -> ConnectionPool[Any]:
    """Get database connection pool."""
    global _db_pool
    if _db_pool is None:
        _db_pool = ConnectionPool(
            lambda: None,  # Placeholder - actual connection factory
            PoolConfig(max_size=10, min_size=2)
        )
    return _db_pool


def get_cache_pool() -> ConnectionPool[Any]:
    """Get cache connection pool."""
    global _cache_pool
    if _cache_pool is None:
        _cache_pool = ConnectionPool(
            lambda: None,  # Placeholder
            PoolConfig(max_size=20, min_size=2)
        )
    return _cache_pool


__all__ = [
    "PoolConfig",
    "PoolStats",
    "PooledConnection",
    "ConnectionPool",
    "get_db_pool",
    "get_cache_pool",
]
