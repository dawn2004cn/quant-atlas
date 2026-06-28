from __future__ import annotations
"""Abstract repository layer using domain models."""


from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class Repository(ABC, Generic[T]):
    """Abstract repository interface."""

    @abstractmethod
    def get_by_id(self, id: str) -> T | None:
        """Get entity by ID."""
        pass

    @abstractmethod
    def get_all(self, limit: int = 100) -> list[T]:
        """Get all entities."""
        pass

    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete an entity."""
        pass

    @abstractmethod
    def find_by(self, **filters) -> list[T]:
        """Find entities by filters."""
        pass


class InMemoryRepository(Repository[T]):
    """In-memory repository implementation."""

    def __init__(self):
        self._storage: dict[str, dict] = {}
        self._id_counter = 0

    def get_by_id(self, id: str) -> T | None:
        return self._storage.get(id)

    def get_all(self, limit: int = 100) -> list[T]:
        return list(self._storage.values())[:limit]

    def create(self, entity: T) -> T:
        self._id_counter += 1
        entity_id = str(self._id_counter)
        if isinstance(entity, dict):
            entity["id"] = entity_id
            self._storage[entity_id] = entity
        return entity

    def update(self, entity: T) -> T:
        if isinstance(entity, dict):
            entity_id = entity.get("id")
            if entity_id and entity_id in self._storage:
                self._storage[entity_id].update(entity)
        return entity

    def delete(self, id: str) -> bool:
        if id in self._storage:
            del self._storage[id]
            return True
        return False

    def find_by(self, **filters) -> list[T]:
        results = []
        for entity in self._storage.values():
            match = True
            for key, value in filters.items():
                if entity.get(key) != value:
                    match = False
                    break
            if match:
                results.append(entity)
        return results


class StockRepository(InMemoryRepository):
    """Stock repository implementation."""

    def find_by_code(self, code: str) -> dict | None:
        """Find stock by code."""
        results = self.find_by(code=code)
        return results[0] if results else None

    def find_by_market(self, market: str) -> list[dict]:
        """Find stocks by market."""
        return self.find_by(market=market)

    def find_by_industry(self, industry: str) -> list[dict]:
        """Find stocks by industry."""
        return self.find_by(industry=industry)


class QuoteRepository(InMemoryRepository):
    """Quote repository implementation."""

    def find_by_code(self, code: str) -> dict | None:
        """Find quote by code."""
        results = self.find_by(code=code)
        return results[0] if results else None

    def find_recent(self, limit: int = 50) -> list[dict]:
        """Get recent quotes."""
        return self.get_all(limit)


class WatchlistRepository(InMemoryRepository):
    """Watchlist repository implementation."""

    def find_by_user(self, user_id: str) -> list[dict]:
        """Find watchlists by user."""
        return self.find_by(user_id=user_id)

    def find_default(self, user_id: str) -> dict | None:
        """Find default watchlist for user."""
        results = self.find_by(user_id=user_id, is_default=True)
        return results[0] if results else None


class PositionRepository(InMemoryRepository):
    """Position repository implementation."""

    def find_by_user(self, user_id: str) -> list[dict]:
        """Find positions by user."""
        return self.find_by(user_id=user_id)

    def find_open_positions(self, user_id: str) -> list[dict]:
        """Find open positions."""
        return self.find_by(user_id=user_id, status="open")

    def find_by_code(self, user_id: str, code: str) -> dict | None:
        """Find position by code."""
        results = self.find_by(user_id=user_id, code=code, status="open")
        return results[0] if results else None


class SignalRepository(InMemoryRepository):
    """Signal repository implementation."""

    def find_by_code(self, code: str) -> list[dict]:
        """Find signals by code."""
        return self.find_by(code=code)

    def find_by_type(self, signal_type: str) -> list[dict]:
        """Find signals by type."""
        return self.find_by(signal_type=signal_type)

    def find_active(self, limit: int = 100) -> list[dict]:
        """Find active signals."""
        return self.get_all(limit)


class AlertRepository(InMemoryRepository):
    """Alert repository implementation."""

    def find_by_user(self, user_id: str) -> list[dict]:
        """Find alerts by user."""
        return self.find_by(user_id=user_id)

    def find_unread(self, user_id: str) -> list[dict]:
        """Find unread alerts."""
        return self.find_by(user_id=user_id, is_read=False)


_stock_repo = StockRepository()
_quote_repo = QuoteRepository()
_watchlist_repo = WatchlistRepository()
_position_repo = PositionRepository()
_signal_repo = SignalRepository()
_alert_repo = AlertRepository()


def get_stock_repository() -> StockRepository:
    """Get stock repository."""
    return _stock_repo


def get_quote_repository() -> QuoteRepository:
    """Get quote repository."""
    return _quote_repo


def get_watchlist_repository() -> WatchlistRepository:
    """Get watchlist repository."""
    return _watchlist_repo


def get_position_repository() -> PositionRepository:
    """Get position repository."""
    return _position_repo


def get_signal_repository() -> SignalRepository:
    """Get signal repository."""
    return _signal_repo


def get_alert_repository() -> AlertRepository:
    """Get alert repository."""
    return _alert_repo


__all__ = [
    "Repository",
    "InMemoryRepository",
    "StockRepository",
    "QuoteRepository",
    "WatchlistRepository",
    "PositionRepository",
    "SignalRepository",
    "AlertRepository",
    "get_stock_repository",
    "get_quote_repository",
    "get_watchlist_repository",
    "get_position_repository",
    "get_signal_repository",
    "get_alert_repository",
]
