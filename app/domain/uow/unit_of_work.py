from __future__ import annotations
"""Unit of Work interface."""


from abc import ABC, abstractmethod
from types import TracebackType

class IUnitOfWork(ABC):
    """Transaction management contract."""

    @abstractmethod
    def __enter__(self) -> IUnitOfWork:
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        """Commit transaction."""
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        """Rollback transaction."""
        raise NotImplementedError
