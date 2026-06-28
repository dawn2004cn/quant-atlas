from __future__ import annotations
"""Generic Repository pattern implementation.

Usage:
    class UserRepo(BaseRepository[UserModel]):
        def __init__(self, session_factory):
            super().__init__(session_factory, UserModel)

        def find_active(self) -> list[UserModel]:
            return self._list(self._select().where(UserModel.is_active.is_(True)))
"""


from typing import Any, Generic, TypeVar
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic base class for SQLAlchemy-backed repositories."""

    def __init__(self, session_factory: Callable[[], Session], model_class: type[T]) -> None:
        self.session_factory = session_factory
        self.model_class = model_class

    def _session(self) -> Session:
        return self.session_factory()

    def _select(self):
        return select(self.model_class)

    def get_by_id(self, entity_id: Any) -> T | None:
        """Fetch an entity by primary key."""
        session = self._session()
        try:
            return session.get(self.model_class, entity_id)
        finally:
            session.close()

    def list_all(self, limit: int = 100) -> list[T]:
        """Fetch all entities."""
        session = self._session()
        try:
            return list(session.scalars(self._select().limit(limit)).all())
        finally:
            session.close()

    def _list(self, stmt) -> list[T]:
        session = self._session()
        try:
            return list(session.scalars(stmt).all())
        finally:
            session.close()

    def add(self, entity: T) -> T:
        """Add an entity and return it with generated ID."""
        session = self._session()
        try:
            session.add(entity)
            session.flush()
            session.commit()
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update(self, entity_id: Any, **values: Any) -> T | None:
        """Partial update by primary key."""
        session = self._session()
        try:
            entity = session.get(self.model_class, entity_id)
            if entity is None:
                return None
            for k, v in values.items():
                setattr(entity, k, v)
            session.commit()
            return entity
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, entity_id: Any) -> bool:
        """Delete an entity by primary key. Returns True if deleted."""
        session = self._session()
        try:
            entity = session.get(self.model_class, entity_id)
            if entity is None:
                return False
            session.delete(entity)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
