from __future__ import annotations
"""
Repository Base Classes with Design Patterns

Design Patterns Applied:
- Repository: Data access abstraction
- Unit of Work: Transaction management
- Specification: Business rule encapsulation
- Factory: Repository creation
- Proxy: Lazy loading
- Decorator: Caching layer
"""


from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, Callable, Type, Protocol, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from app.core.patterns.creational import Singleton, Factory
from app.core.patterns.architectural import Specification, UnitOfWork

from ..mysql.mysql_repositories import MySQLRepositoryBase


T = TypeVar('T')
TId = TypeVar('TId')


class RepositoryBase(ABC, Generic[T, TId]):
    """Abstract base repository."""
    
    @abstractmethod
    def find_by_id(self, id: TId) -> T | None:
        pass
    
    @abstractmethod
    def find_all(self) -> list[T]:
        pass
    
    @abstractmethod
    def find_by_spec(self, spec: Specification) -> list[T]:
        pass
    
    @abstractmethod
    def save(self, entity: T) -> T:
        pass
    
    @abstractmethod
    def delete(self, id: TId) -> bool:
        pass
    
    @abstractmethod
    def count(self) -> int:
        pass


@dataclass
class Entity:
    """Base entity."""
    id: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TradeEntity(Entity):
    """Trade entity."""
    symbol: str = ""
    name: str = ""
    strategy: str = ""
    direction: str = ""
    price: float = 0.0
    quantity: int = 0
    amount: float = 0.0
    trade_time: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0
    status: str = ""


class TradeSpecification(Specification):
    """Specification for trade filtering."""
    
    def __init__(
        self,
        symbol: str | None = None,
        status: str | None = None,
        strategy: str | None = None,
        direction: str | None = None,
    ) -> None:
        self._symbol = symbol
        self._status = status
        self._strategy = strategy
        self._direction = direction
    
    def is_satisfied_by(self, candidate: Any) -> bool:
        if not isinstance(candidate, TradeEntity):
            return False
        if self._symbol and candidate.symbol != self._symbol:
            return False
        if self._status and candidate.status != self._status:
            return False
        if self._strategy and candidate.strategy != self._strategy:
            return False
        if self._direction and candidate.direction != self._direction:
            return False
        return True


class InMemoryTradeRepository(RepositoryBase[TradeEntity, int]):
    """In-memory trade repository."""
    
    def __init__(self) -> None:
        self._storage: dict[int, TradeEntity] = {}
        self._next_id = 1
    
    def find_by_id(self, id: int) -> TradeEntity | None:
        return self._storage.get(id)
    
    def find_all(self) -> list[TradeEntity]:
        return list(self._storage.values())
    
    def find_by_spec(self, spec: Specification) -> list[TradeEntity]:
        return [e for e in self._storage.values() if spec.is_satisfied_by(e)]
    
    def save(self, entity: TradeEntity) -> TradeEntity:
        if entity.id == 0:
            entity.id = self._next_id
            self._next_id += 1
        entity.updated_at = datetime.now()
        self._storage[entity.id] = entity
        return entity
    
    def delete(self, id: int) -> bool:
        return self._storage.pop(id, None) is not None
    
    def count(self) -> int:
        return len(self._storage)
    
    def find_by_symbol(self, symbol: str) -> list[TradeEntity]:
        return [e for e in self._storage.values() if e.symbol == symbol]
    
    def find_holding_positions(self) -> list[TradeEntity]:
        return [e for e in self._storage.values() if e.status == "holding"]
    
    def find_closed_positions(self) -> list[TradeEntity]:
        return [e for e in self._storage.values() if e.status.startswith("closed")]


class TradeUnitOfWork(UnitOfWork):
    """Unit of Work for trade operations."""
    
    def __init__(self, repository: InMemoryTradeRepository) -> None:
        self._repository = repository
        self._new: list[TradeEntity] = []
        self._dirty: list[TradeEntity] = []
        self._deleted: list[int] = []
    
    def begin(self) -> None:
        pass
    
    def commit(self) -> None:
        for entity in self._new:
            self._repository.save(entity)
        for entity in self._dirty:
            self._repository.save(entity)
        for entity_id in self._deleted:
            self._repository.delete(entity_id)
        self._clear()
    
    def rollback(self) -> None:
        self._clear()
    
    def register_new(self, entity: TradeEntity) -> None:
        self._new.append(entity)
    
    def register_dirty(self, entity: TradeEntity) -> None:
        if entity not in self._dirty and entity not in self._new:
            self._dirty.append(entity)
    
    def register_deleted(self, entity: TradeEntity) -> None:
        if entity.id not in self._deleted:
            self._deleted.append(entity.id)
    
    def _clear(self) -> None:
        self._new.clear()
        self._dirty.clear()
        self._deleted.clear()


class RepositoryRegistry(Factory):
    """Registry for repositories."""
    
    def __init__(self) -> None:
        super().__init__()
        self._repositories: dict[type, RepositoryBase] = {}
    
    def register_repository(self, entity_type: type, repository: RepositoryBase) -> None:
        self._repositories[entity_type] = repository
    
    def get_repository(self, entity_type: type) -> RepositoryBase | None:
        return self._repositories.get(entity_type)


class CachedRepository(Generic[T, TId]):
    """Decorator for caching repository."""
    
    def __init__(self, wrapped: RepositoryBase[T, TId]) -> None:
        self._wrapped = wrapped
        self._cache: dict[TId, T] = {}
    
    def find_by_id(self, id: TId) -> T | None:
        if id in self._cache:
            return self._cache[id]
        result = self._wrapped.find_by_id(id)
        if result:
            self._cache[id] = result
        return result
    
    def invalidate_cache(self) -> None:
        self._cache.clear()
    
    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)


class LazyRepository(Generic[T, TId]):
    """Proxy pattern for lazy loading."""
    
    def __init__(self, factory: Callable[[], RepositoryBase[T, TId]]) -> None:
        self._factory = factory
        self._instance: RepositoryBase[T, TId] | None = None
    
    def _get_instance(self) -> RepositoryBase[T, TId]:
        if self._instance is None:
            self._instance = self._factory()
        return self._instance
    
    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_instance(), name)


__all__ = [
    'RepositoryBase',
    'Entity',
    'TradeEntity',
    'TradeSpecification',
    'InMemoryTradeRepository',
    'TradeUnitOfWork',
    'RepositoryRegistry',
    'CachedRepository',
    'LazyRepository',
]