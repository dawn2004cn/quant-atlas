from __future__ import annotations
"""Enhanced Async Repository Base.

Phase 46: 增强版异步 Repository 基类，提供通用异步操作。

This module provides a comprehensive async repository base class
with common CRUD operations, pagination, and transaction support.
"""


from typing import Any, Generic, TypeVar
from collections.abc import Sequence
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete, func
from sqlalchemy.sql import Select

T = TypeVar("T")


class AsyncRepositoryBase(Generic[T]):
    """Enhanced async repository base class.

    Provides:
    - Async CRUD operations
    - Pagination support
    - Transaction management
    - Query building helpers

    Usage:
        class UserRepository(AsyncRepositoryBase[User]):
            def __init__(self, session_factory):
                super().__init__(session_factory, User)

            async def get_by_username(self, username: str) -> User | None:
                stmt = self._select().where(User.username == username)
                return await self._get_one(stmt)
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        model_class: type[T],
    ):
        self._session_factory = session_factory
        self._model_class = model_class

    def _select(self) -> Select:
        """Create a base select statement."""
        return select(self._model_class)

    async def _get_one(self, stmt: Select) -> T | None:
        """Execute a select statement and return one result."""
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return result.scalars().first()

    async def _get_all(self, stmt: Select) -> Sequence[T]:
        """Execute a select statement and return all results."""
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def _execute(self, stmt) -> int:
        """Execute a statement and return affected row count."""
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount if hasattr(result, "rowcount") else 0

    async def get_by_id(self, id: Any) -> T | None:
        """Get entity by ID."""
        stmt = self._select().where(self._model_class.id == id)
        return await self._get_one(stmt)

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by=None,
    ) -> Sequence[T]:
        """List all entities with pagination."""
        stmt = self._select().offset(offset).limit(limit)
        if order_by:
            stmt = stmt.order_by(order_by)
        return await self._get_all(stmt)

    async def count(self, where=None) -> int:
        """Count entities."""
        async with self._session_factory() as session:
            stmt = select(func.count()).select_from(self._model_class)
            if where:
                stmt = stmt.where(where)
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        async with self._session_factory() as session:
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            return entity

    async def update(self, id: Any, data: dict[str, Any]) -> bool:
        """Update entity by ID."""
        stmt = (
            update(self._model_class)
            .where(self._model_class.id == id)
            .values(**data)
        )
        return await self._execute(stmt) > 0

    async def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        stmt = delete(self._model_class).where(self._model_class.id == id)
        return await self._execute(stmt) > 0

    async def exists(self, where) -> bool:
        """Check if entity exists."""
        async with self._session_factory() as session:
            stmt = select(func.count()).select_from(self._model_class).where(where)
            result = await session.execute(stmt)
            return (result.scalar() or 0) > 0


class AsyncUnitOfWork:
    """Async Unit of Work for transaction management.

    Usage:
        async with AsyncUnitOfWork(session_factory) as uow:
            user = await uow.users.get_by_id(1)
            user.name = "new name"
            await uow.commit()
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncUnitOfWork:
        self._session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self._session.rollback()
        else:
            await self._session.commit()
        await self._session.close()

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._session:
            await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._session:
            await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        """Get the current session."""
        if self._session is None:
            raise RuntimeError("Unit of work not started")
        return self._session


__all__ = ["AsyncRepositoryBase", "AsyncUnitOfWork"]
