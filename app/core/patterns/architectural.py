from __future__ import annotations

"""
Architectural Design Patterns
==============================

23. Repository - Data access abstraction
24. Unit of Work - Transaction management
25. Service Layer - Business logic encapsulation
26. CQRS - Command/Query separation
27. Dependency Injection - Loose coupling
28. Event Sourcing - Store events not state
29. Specification - Business rule encapsulation
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Generic, Protocol, TypeVar

T = TypeVar('T')
TEntity = TypeVar('TEntity')
TId = TypeVar('TId')


class RepositoryProtocol(Protocol[TEntity, TId]):
    """Protocol defining repository interface."""

    def find_by_id(self, id: TId) -> TEntity | None:
        ...

    def find_all(self) -> list[TEntity]:
        ...

    def save(self, entity: TEntity) -> TEntity:
        ...

    def delete(self, id: TId) -> bool:
        ...


class Repository(ABC, Generic[TEntity, TId]):
    """Abstract repository base class."""

    @abstractmethod
    def find_by_id(self, id: TId) -> TEntity | None:
        """Find entity by ID."""
        pass

    @abstractmethod
    def find_all(self) -> list[TEntity]:
        """Find all entities."""
        pass

    @abstractmethod
    def find_by_filter(self, filter_fn: Callable[[TEntity], bool]) -> list[TEntity]:
        """Find entities matching filter."""
        pass

    @abstractmethod
    def save(self, entity: TEntity) -> TEntity:
        """Save or update entity."""
        pass

    @abstractmethod
    def delete(self, id: TId) -> bool:
        """Delete entity by ID."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Count total entities."""
        pass


class InMemoryRepository(Repository[TEntity, TId]):
    """In-memory repository implementation."""

    def __init__(self) -> None:
        self._storage: dict[TId, TEntity] = {}
        self._id_generator: Callable[[], TId] = lambda: len(self._storage) + 1

    def set_id_generator(self, generator: Callable[[], TId]) -> None:
        self._id_generator = generator

    def find_by_id(self, id: TId) -> TEntity | None:
        return self._storage.get(id)

    def find_all(self) -> list[TEntity]:
        return list(self._storage.values())

    def find_by_filter(self, filter_fn: Callable[[TEntity], bool]) -> list[TEntity]:
        return [e for e in self._storage.values() if filter_fn(e)]

    def save(self, entity: TEntity) -> TEntity:
        return entity

    def delete(self, id: TId) -> bool:
        return self._storage.pop(id, None) is not None

    def count(self) -> int:
        return len(self._storage)


class Specification(ABC):
    """Abstract specification."""

    @abstractmethod
    def is_satisfied_by(self, candidate: Any) -> bool:
        """Check if candidate satisfies specification."""
        pass

    def and_spec(self, other: Specification) -> Specification:
        return AndSpecification(self, other)

    def or_spec(self, other: Specification) -> Specification:
        return OrSpecification(self, other)

    def not_spec(self) -> Specification:
        return NotSpecification(self)


class AndSpecification(Specification):
    def __init__(self, left: Specification, right: Specification) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: Any) -> bool:
        return (self._left.is_satisfied_by(candidate) and
                self._right.is_satisfied_by(candidate))


class OrSpecification(Specification):
    def __init__(self, left: Specification, right: Specification) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: Any) -> bool:
        return (self._left.is_satisfied_by(candidate) or
                self._right.is_satisfied_by(candidate))


class NotSpecification(Specification):
    def __init__(self, spec: Specification) -> None:
        self._spec = spec

    def is_satisfied_by(self, candidate: Any) -> bool:
        return not self._spec.is_satisfied_by(candidate)


class UnitOfWork(ABC):
    """Abstract unit of work."""

    @abstractmethod
    def begin(self) -> None:
        """Begin transaction."""
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit transaction."""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rollback transaction."""
        pass

    @abstractmethod
    def register_new(self, entity: Any) -> None:
        """Register new entity."""
        pass

    @abstractmethod
    def register_dirty(self, entity: Any) -> None:
        """Register modified entity."""
        pass

    @abstractmethod
    def register_deleted(self, entity: Any) -> None:
        """Register deleted entity."""
        pass


class InMemoryUnitOfWork(UnitOfWork):
    """In-memory unit of work implementation."""

    def __init__(self) -> None:
        self._new: list[Any] = []
        self._dirty: list[Any] = []
        self._deleted: list[Any] = []
        self._committed = False

    def begin(self) -> None:
        self._committed = False

    def commit(self) -> None:
        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()
        self._committed = True

    def rollback(self) -> None:
        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()
        self._committed = False

    def register_new(self, entity: Any) -> None:
        self._new.append(entity)

    def register_dirty(self, entity: Any) -> None:
        if entity not in self._dirty and entity not in self._new:
            self._dirty.append(entity)

    def register_deleted(self, entity: Any) -> None:
        self._deleted.append(entity)


class ServiceLayer(ABC):
    """Abstract service layer."""

    @abstractmethod
    def execute(self, request: Any) -> Any:
        """Execute service operation."""
        pass


class UseCase(ABC):
    """Abstract use case."""

    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Execute use case."""
        pass


class Command(UseCase):
    """Command for CQRS."""

    def __init__(self, handler: Callable[[Any], Any]) -> None:
        self._handler = handler

    def execute(self, input_data: Any) -> Any:
        return self._handler(input_data)


class Query(UseCase):
    """Query for CQRS."""

    def __init__(self, handler: Callable[[Any], Any]) -> None:
        self._handler = handler

    def execute(self, input_data: Any) -> Any:
        return self._handler(input_data)


class CommandHandler(ABC):
    """Abstract command handler."""

    @abstractmethod
    def handle(self, command: Command) -> Any:
        pass


class QueryHandler(ABC):
    """Abstract query handler."""

    @abstractmethod
    def handle(self, query: Query) -> Any:
        pass


class CqrsDispatcher:
    """CQRS dispatcher."""

    def __init__(self) -> None:
        self._command_handlers: dict[type, CommandHandler] = {}
        self._query_handlers: dict[type, QueryHandler] = {}

    def register_command(self, command_type: type, handler: CommandHandler) -> None:
        self._command_handlers[command_type] = handler

    def register_query(self, query_type: type, handler: QueryHandler) -> None:
        self._query_handlers[query_type] = handler

    def dispatch_command(self, command: Command) -> Any:
        handler = self._command_handlers.get(type(command))
        if handler:
            return handler.handle(command)
        return None

    def dispatch_query(self, query: Query) -> Any:
        handler = self._query_handlers.get(type(query))
        if handler:
            return handler.handle(query)
        return None


class DependencyContainer:
    """Simple dependency injection container."""

    def __init__(self) -> None:
        self._services: dict[type, object] = {}
        self._factories: dict[type, Callable[[], object]] = {}

    def register_singleton(self, interface: type, instance: object) -> None:
        self._services[interface] = instance

    def register_factory(self, interface: type, factory: Callable[[], object]) -> None:
        self._factories[interface] = factory

    def resolve(self, interface: type) -> object:
        if interface in self._services:
            return self._services[interface]
        if interface in self._factories:
            return self._factories[interface]()
        raise ValueError(f"Service not registered: {interface}")


class EventType(Enum):
    """Event types for event sourcing."""
    CREATED = auto()
    UPDATED = auto()
    DELETED = auto()
    CUSTOM = auto()


@dataclass
class DomainEvent:
    """Base domain event."""

    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    payload: dict[str, Any] = field(default_factory=dict)


class EventStore(ABC):
    """Abstract event store."""

    @abstractmethod
    def append(self, event: DomainEvent) -> None:
        """Append event."""
        pass

    @abstractmethod
    def get_events_for_aggregate(self, aggregate_id: str) -> list[DomainEvent]:
        """Get events for aggregate."""
        pass


class InMemoryEventStore(EventStore):
    """In-memory event store."""

    def __init__(self) -> None:
        self._events: dict[str, list[DomainEvent]] = {}

    def append(self, event: DomainEvent) -> None:
        aggregate_id = event.payload.get("aggregate_id", "default")
        if aggregate_id not in self._events:
            self._events[aggregate_id] = []
        self._events[aggregate_id].append(event)

    def get_events_for_aggregate(self, aggregate_id: str) -> list[DomainEvent]:
        return self._events.get(aggregate_id, [])


class AggregateRoot:
    """Base aggregate root."""

    def __init__(self, aggregate_id: str) -> None:
        self._aggregate_id = aggregate_id
        self._uncommitted_events: list[DomainEvent] = []

    def add_event(self, event: DomainEvent) -> None:
        self._uncommitted_events.append(event)

    def pull_uncommitted_events(self) -> list[DomainEvent]:
        events = self._uncommitted_events.copy()
        self._uncommitted_events.clear()
        return events


class PipelineBehavior(ABC):
    """Pipeline behavior for middleware pattern."""

    @abstractmethod
    def invoke(self, request: Any, next_handler: Callable[[], Any]) -> Any:
        pass


class LoggingBehavior(PipelineBehavior):
    """Logging behavior."""

    def invoke(self, request: Any, next_handler: Callable[[], Any]) -> Any:
        print(f"Before: {request}")
        result = next_handler()
        print(f"After: {result}")
        return result


class ErrorHandlingBehavior(PipelineBehavior):
    """Error handling behavior."""

    def invoke(self, request: Any, next_handler: Callable[[], Any]) -> Any:
        try:
            return next_handler()
        except Exception as e:
            print(f"Error handled: {e}")
            raise


class Mediator:
    """Mediator for request/response."""

    def __init__(self) -> None:
        self._behaviors: list[PipelineBehavior] = []
        self._handlers: dict[type, Callable] = {}

    def add_behavior(self, behavior: PipelineBehavior) -> None:
        self._behaviors.append(behavior)

    def register_handler(self, request_type: type, handler: Callable) -> None:
        self._handlers[request_type] = handler

    def send(self, request: Any) -> Any:
        def build_pipeline(index: int) -> Callable[[], Any]:
            if index >= len(self._behaviors):
                return lambda: self._handlers[type(request)](request)

            behavior = self._behaviors[index]
            next_handler = build_pipeline(index + 1)
            return lambda: behavior.invoke(request, next_handler)

        if type(request) in self._handlers:
            return build_pipeline(0)()
        return None


__all__ = [
    'RepositoryProtocol',
    'Repository',
    'InMemoryRepository',
    'Specification',
    'AndSpecification',
    'OrSpecification',
    'NotSpecification',
    'UnitOfWork',
    'InMemoryUnitOfWork',
    'ServiceLayer',
    'UseCase',
    'Command',
    'Query',
    'CommandHandler',
    'QueryHandler',
    'CqrsDispatcher',
    'DependencyContainer',
    'EventType',
    'DomainEvent',
    'EventStore',
    'InMemoryEventStore',
    'AggregateRoot',
    'PipelineBehavior',
    'LoggingBehavior',
    'ErrorHandlingBehavior',
    'Mediator',
]
