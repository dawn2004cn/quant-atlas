from __future__ import annotations
"""Pagination utilities for domain queries."""


import math
from dataclasses import dataclass
from typing import Generic, TypeVar
from collections.abc import Callable

T = TypeVar('T')


@dataclass
class Page(Generic[T]):
    """A page of results."""
    items: list[T]
    page: int
    page_size: int
    total_items: int

    @property
    def total_pages(self) -> int:
        return math.ceil(self.total_items / self.page_size) if self.page_size else 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def start_index(self) -> int:
        return (self.page - 1) * self.page_size + 1

    @property
    def end_index(self) -> int:
        return min(self.page * self.page_size, self.total_items)


def paginate(
    items: list[T],
    page: int = 1,
    page_size: int = 20
) -> Page[T]:
    """Paginate a list of items."""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    return Page(
        items=items[start:end],
        page=page,
        page_size=page_size,
        total_items=total
    )


def paginate_query(
    query_fn: Callable[[int, int], list[T]],
    page: int = 1,
    page_size: int = 20,
    total_fn: Callable[[], int] | None = None
) -> Page[T]:
    """Paginate a database query."""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    total = total_fn() if total_fn else 0
    offset = (page - 1) * page_size

    items = query_fn(offset, page_size)

    return Page(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total
    )


class Paginator:
    """Paginator for iterables."""

    def __init__(self, items: list[T], page_size: int = 20):
        self._items = items
        self._page_size = page_size

    def get_page(self, page: int) -> Page[T]:
        return paginate(self._items, page, self._page_size)

    def get_all_pages(self) -> list[Page[T]]:
        total_pages = math.ceil(len(self._items) / self._page_size)
        return [self.get_page(i) for i in range(1, total_pages + 1)]


__all__ = ["Page", "paginate", "paginate_query", "Paginator"]
