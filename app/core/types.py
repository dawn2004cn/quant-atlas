from __future__ import annotations

"""Common type definitions for quant-atlas.

This module provides shared types used across all layers:
- Result types for operations
- Pagination types
- API response types
- Event types
"""


from collections.abc import AsyncGenerator, Generator
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Result(Generic[T]):
    """Represents a successful result."""

    data: T


@dataclass(frozen=True)
class Error(Generic[E]):
    """Represents an error result."""

    error: E
    message: str


@dataclass(frozen=True)
class PageParams:
    """Pagination parameters."""

    offset: int = 0
    limit: int = 20
    sort_by: str | None = None
    order: str = "asc"

    def __post_init__(self) -> None:
        if self.limit > 100:
            self.limit = 100
        if self.offset < 0:
            self.offset = 0
        if self.order not in ("asc", "desc"):
            self.order = "asc"


@dataclass(frozen=True)
class PageResult(Generic[T]):
    """Paginated result."""

    items: list[T]
    total: int
    offset: int
    limit: int

    @property
    def has_more(self) -> bool:
        return self.offset + self.limit < self.total


@dataclass(frozen=True)
class ApiResponse:
    """Standard API response wrapper."""

    status: str = "ok"
    data: Any = None
    error_msg: str | None = None
    message: str | None = None

    @classmethod
    def ok(cls, data: Any = None, message: str | None = None) -> ApiResponse:
        return cls(status="ok", data=data, message=message)

    @classmethod
    def error(cls, message: str, error_code: str | None = None) -> ApiResponse:
        return cls(status="error", error_msg=error_code or "error", message=message)


@dataclass(frozen=True)
class EmptyResult:
    """Represents an empty result or void return."""



AsyncIterator = AsyncGenerator[T, None]
SyncIterator = Generator[T, None, None]
