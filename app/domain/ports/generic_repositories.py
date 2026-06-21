from __future__ import annotations
"""Generic Repository base interfaces."""


from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

T = TypeVar('T')


@dataclass
class PageRequest:
    """Pagination request."""
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "asc"


@dataclass
class PageResult(Generic[T]):
    """Pagination result."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


@dataclass
class FilterCondition:
    """Filter condition for queries."""
    field: str
    operator: str  # "eq", "ne", "gt", "lt", "in", "like"
    value: Any


class IRepository(ABC, Generic[T]):
    """Generic repository interface.

    All data access repositories should implement this interface.
    """

    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[T]:
        """Get all entities."""
        raise NotImplementedError

    @abstractmethod
    def create(self, entity: T) -> str:
        """Create entity and return ID."""
        raise NotImplementedError

    @abstractmethod
    def update(self, id: str, data: dict[str, Any]) -> bool:
        """Update entity."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete entity."""
        raise NotImplementedError

    def find_by(self, **filters) -> List[T]:
        """Find by keyword arguments."""
        raise NotImplementedError

    def find_one_by(self, **filters) -> Optional[T]:
        """Find one by keyword arguments."""
        raise NotImplementedError

    def find_paginated(self, page: int, page_size: int, **filters) -> PageResult[T]:
        """Find with pagination."""
        raise NotImplementedError


class IStockRepository(ABC):
    """Stock data repository interface."""

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[dict]:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> List[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_by_industry(self, industry: str) -> List[dict]:
        raise NotImplementedError


class ITradeRepository(ABC):
    """Trade repository interface."""

    @abstractmethod
    def get_positions(self, user_id: str) -> List[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_orders(self, user_id: str, status: Optional[str] = None) -> List[dict]:
        raise NotImplementedError

    @abstractmethod
    def create_order(self, order: dict) -> str:
        raise NotImplementedError


class IUoW(ABC):
    """Unit of Work pattern for transaction management."""

    @abstractmethod
    def begin(self) -> None:
        """Begin transaction."""
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        """Commit transaction."""
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        """Rollback transaction."""
        raise NotImplementedError


class BaseRepository(ABC):
    """Base class for repositories with common functionality."""

    def _apply_filters(self, items: List[dict], filters: dict) -> List[dict]:
        """Apply filters to list of items."""
        result = items
        for key, value in filters.items():
            if value is None:
                continue
            result = [item for item in result if item.get(key) == value]
        return result

    def _paginate(self, items: List[T], page: int, page_size: int) -> PageResult[T]:
        """Apply pagination."""
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return PageResult(
            items=items[start:end],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )


__all__ = [
    "PageRequest",
    "PageResult",
    "FilterCondition",
    "IRepository",
    "IStockRepository",
    "ITradeRepository",
    "IUoW",
    "BaseRepository"
]