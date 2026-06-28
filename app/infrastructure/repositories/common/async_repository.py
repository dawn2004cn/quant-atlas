from __future__ import annotations
"""Async Repository pattern for database operations.

Following Phase 6: Reactive Architecture - adding async support to data layer.
"""


from typing import Any, Generic, TypeVar
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update
from sqlalchemy.orm import DeclarativeBase

from app.core.logger import get_logger
from app.config import AppSettings

logger = get_logger(__name__)

T = TypeVar('T')


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


@dataclass
class AsyncRepository(Generic[T]):
    """Async repository for database operations.

    Usage:
        class UserRepository(AsyncRepository[User]):
            pass

        repo = UserRepository(User, session)
        users = await repo.find_all()
        user = await repo.find_by_id(1)
    """

    model: type[T]
    session: AsyncSession

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Find all records."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_id(self, id: int) -> T | None:
        """Find by primary key."""
        return await self.session.get(self.model, id)

    async def find_by(self, **kwargs) -> list[T]:
        """Find by filter criteria."""
        stmt = select(self.model)
        for key, value in kwargs.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_one(self, **kwargs) -> T | None:
        """Find single record."""
        results = await self.find_by(**kwargs)
        return results[0] if results else None

    async def create(self, **kwargs) -> T:
        """Create new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: int, **kwargs) -> bool:
        """Update record by ID."""
        stmt = update(self.model).where(self.model.id == id).values(**kwargs)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def delete(self, id: int) -> bool:
        """Delete record by ID."""
        instance = await self.find_by_id(id)
        if instance:
            await self.session.delete(instance)
            await self.session.flush()
            return True
        return False

    async def count(self) -> int:
        """Count total records."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class AsyncUnitOfWork:
    """Async Unit of Work pattern for transaction management.

    Usage:
        async with AsyncUnitOfWork(session_factory) as uow:
            user = await uow.users.create(name="test")
            await uow.commit()
    """

    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncUnitOfWork:
        self._session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        await self._session.close()

    async def commit(self):
        """Commit transaction."""
        if self._session:
            await self._session.commit()

    async def rollback(self):
        """Rollback transaction."""
        if self._session:
            await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        """Get current session."""
        if not self._session:
            raise RuntimeError("Session not initialized. Use 'async with' context.")
        return self._session


# Global async engine and session factory
_async_engine = None
_async_session_factory = None


def get_async_engine(settings: AppSettings) -> Any:
    """Get or create async engine."""
    global _async_engine

    if _async_engine is None:
        # Convert sync DB URL to async
        db_url = settings.database_uri
        if db_url.startswith('sqlite'):
            db_url = db_url.replace('sqlite://', 'sqlite+aiosqlite://')
        elif db_url.startswith('mysql'):
            db_url = db_url.replace('mysql://', 'mysql+aiomysql://')
        elif db_url.startswith('postgresql'):
            db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')

        _async_engine = create_async_engine(
            db_url,
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
        )

    return _async_engine


def get_async_session_factory(settings: AppSettings) -> async_sessionmaker:
    """Get or create async session factory."""
    global _async_session_factory

    if _async_session_factory is None:
        engine = get_async_engine(settings)
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _async_session_factory


async def init_async_db(settings: AppSettings):
    """Initialize async database connections."""
    engine = get_async_engine(settings)
    logger.info("Async database initialized: %s", engine.url)


async def close_async_db():
    """Close async database connections."""
    global _async_engine, _async_session_factory

    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Async database closed")
