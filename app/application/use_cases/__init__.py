from __future__ import annotations
"""UseCase base classes - Application business logic abstraction."""


from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class UseCaseResult:
    """UseCase execution result container."""
    success: bool
    data: Any = None
    error: str | None = None

    @staticmethod
    def ok(data: Any = None) -> UseCaseResult:
        return UseCaseResult(success=True, data=data)

    @staticmethod
    def fail(error: str) -> UseCaseResult:
        return UseCaseResult(success=False, error=error)


class UseCase(ABC):
    """Base UseCase class - enforces single responsibility."""

    @abstractmethod
    def execute(self, *args, **kwargs) -> UseCaseResult:
        """Execute the use case. Must be implemented by subclasses."""
        raise NotImplementedError


class UseCaseFactory(ABC):
    """Factory for creating use case instances with dependencies."""

    @abstractmethod
    def create(self) -> UseCase:
        """Create a use case instance."""
        raise NotImplementedError