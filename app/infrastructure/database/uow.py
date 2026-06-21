from __future__ import annotations
"""SQLAlchemy Unit of Work implementation."""


from sqlalchemy.orm import Session
from app.domain.uow.unit_of_work import IUnitOfWork
from app.infrastructure.database.db_manager import get_db_session

class SqlAlchemyUnitOfWork(IUnitOfWork):
    """SQLAlchemy implementation of Unit of Work."""

    def __init__(self) -> None:
        self.session: Session | None = None

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self.session = get_db_session()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.session.close()

    def commit(self) -> None:
        if self.session:
            self.session.commit()

    def rollback(self) -> None:
        if self.session:
            self.session.rollback()
