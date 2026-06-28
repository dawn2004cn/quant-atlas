from __future__ import annotations
"""Asynchronous MySQL client using SQLAlchemy and asyncmy.

This module provides async database connectivity for Phase 41 migration.
Key improvements over sync pymysql:
- Non-blocking I/O for concurrent data access
- Connection pooling for high throughput scenarios
- Proper async context manager support
"""


from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from ...core.runtime_config import get_runtime_int
from .mysql_settings import MysqlSettings


from app.core.logger import get_logger

logger = get_logger(__name__)


def _build_async_uri(database_uri: str) -> str:
    """Convert sync MySQL URI to async version."""
    if database_uri.startswith("mysql+pymysql://"):
        return database_uri.replace("mysql+pymysql://", "mysql+asyncmy://")
    if database_uri.startswith("mysql://"):
        return database_uri.replace("mysql://", "mysql+asyncmy://")
    return database_uri


def _get_async_engine_kwargs() -> dict:
    """Centralized async engine configuration."""
    pool_size = max(1, get_runtime_int("ASYNC_DB_POOL_SIZE", 10))
    max_overflow = max(0, get_runtime_int("ASYNC_DB_MAX_OVERFLOW", 20))
    pool_recycle = max(60, get_runtime_int("ASYNC_DB_POOL_RECYCLE", 300))
    pool_timeout = max(5, get_runtime_int("ASYNC_DB_POOL_TIMEOUT", 30))

    return {
        "poolclass": AsyncAdaptedQueuePool,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_recycle": pool_recycle,
        "pool_timeout": pool_timeout,
        "pool_pre_ping": True,
        "echo": False,
    }


class AsyncMySQLClient:
    """Async MySQL client with connection pooling.

    Usage:
        client = AsyncMySQLClient(database_uri="mysql+pymysql://...")
        async with client.session() as session:
            result = await session.execute(select(User))
    """

    def __init__(self, database_uri: str):
        self._database_uri = database_uri
        self._async_uri = _build_async_uri(database_uri)
        self._engine_kwargs = _get_async_engine_kwargs()
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                self._async_uri,
                **self._engine_kwargs,
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine,
                expire_on_commit=False,
                class_=AsyncSession,
            )
        return self._session_factory

    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager for session lifecycle.

        Usage:
            async with client.session() as session:
                await session.execute(...)
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_session(self) -> AsyncSession:
        """Get a new session (non-context manager version)."""
        return self.session_factory()

    async def close(self) -> None:
        """Close engine and dispose connection pool."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @classmethod
    def from_mysql_settings(cls, mysql_settings: MysqlSettings) -> AsyncMySQLClient:
        """Create client from MysqlSettings configuration."""
        from urllib.parse import quote_plus
        user = quote_plus(mysql_settings.user or "")
        password = quote_plus(mysql_settings.password or "")
        uri = (
            f"mysql+pymysql://{user}:{password}"
            f"@{mysql_settings.host}:{mysql_settings.port}/{mysql_settings.database}"
        )
        return cls(uri)


async_test_uri = "mysql+asyncmy://admin:@localhost:3307/quant_atlas"


def create_async_session_factory(database_uri: str) -> async_sessionmaker[AsyncSession]:
    """Factory function to create async session maker.

    This is the primary entry point for Phase 41 async migration.
    Use this instead of sync session_factory where async I/O is needed.

    Args:
        database_uri: SQLAlchemy database URI (mysql+pymysql://...)

    Returns:
        async_sessionmaker configured for async operations

    Example:
        factory = create_async_session_factory(database_uri)
        async with factory() as session:
            result = await session.execute(select(Model))
    """
    client = AsyncMySQLClient(database_uri)
    return client.session_factory
