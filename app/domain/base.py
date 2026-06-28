from __future__ import annotations
"""Domain Layer Base - Entities and Value Objects.

This module provides the foundational domain layer components:
- Base Entity class
- Value Objects
- Domain Events
- Repository Interfaces
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4


# =============================================================================
# Entity Base
# =============================================================================

@dataclass
class Entity:
    """Base class for all domain entities."""

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


# =============================================================================
# Value Objects
# =============================================================================

@dataclass(frozen=True)
class DateRange:
    """日期范围值对象."""

    start: datetime
    end: datetime

    def contains(self, dt: datetime) -> bool:
        return self.start <= dt <= self.end

    @property
    def days(self) -> int:
        return (self.end - self.start).days


@dataclass(frozen=True)
class Percentage:
    """百分比值对象."""

    value: float  # 0.0 to 1.0

    @classmethod
    def from_decimal(cls, value: float) -> Percentage:
        return cls(value=value)

    @classmethod
    def from_percent(cls, value: float) -> Percentage:
        return cls(value=value / 100)

    @property
    def decimal(self) -> float:
        return self.value

    @property
    def percent(self) -> float:
        return self.value * 100

    def __str__(self) -> str:
        return f"{self.percent:.2f}%"


@dataclass(frozen=True)
class Money:
    """金额值对象."""

    amount: float
    currency: str = "CNY"

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:,.2f}"


# =============================================================================
# Aggregate Root
# =============================================================================

class AggregateRoot(Entity):
    """Aggregate Root base class."""

    def __init__(self) -> None:
        super().__init__()
        self._domain_events: list[DomainEvent] = []

    def add_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events


# =============================================================================
# Domain Events
# =============================================================================

class DomainEvent:
    """Base domain event."""

    def __init__(self) -> None:
        self._occurred_on: datetime = datetime.now()
        self._event_id: UUID = uuid4()


# =============================================================================
# Repository Interfaces
# =============================================================================

T = TypeVar('T', bound=Entity)


class IRepository(ABC, Generic[T]):
    """Base repository interface."""

    @abstractmethod
    def get(self, id: UUID) -> T | None:
        pass

    @abstractmethod
    def save(self, entity: T) -> T:
        pass

    @abstractmethod
    def delete(self, id: UUID) -> None:
        pass

    @abstractmethod
    def list(self, limit: int = 100) -> list[T]:
        pass


class IQueryRepository(ABC, Generic[T]):
    """Read-only repository interface."""

    @abstractmethod
    def find_by_id(self, id: UUID) -> T | None:
        pass

    @abstractmethod
    def find_all(self, limit: int = 100) -> list[T]:
        pass

    @abstractmethod
    def find_by_criteria(self, **kwargs: Any) -> list[T]:
        pass


# =============================================================================
# Domain Service Interfaces
# =============================================================================

class IDomainService(ABC):
    """Base domain service interface."""
    pass


# =============================================================================
# Factory
# =============================================================================

class EntityFactory(ABC):
    """Factory for creating entities."""

    @staticmethod
    def create(entity_class: type[T], **kwargs: Any) -> T:
        return entity_class(**kwargs)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Entity",
    "AggregateRoot",
    "DateRange",
    "Percentage",
    "Money",
    "DomainEvent",
    "IRepository",
    "IQueryRepository",
    "IDomainService",
    "EntityFactory",
]
