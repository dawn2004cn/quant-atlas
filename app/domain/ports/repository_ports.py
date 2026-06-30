from __future__ import annotations

"""Repository ports for domain persistence.

These are abstract interfaces that infrastructure repositories must implement.
"""


from abc import ABC, abstractmethod
from typing import Any

from app.domain.shared.value_objects import UserAccount


class IBasicMarketDataRepository(ABC):
    """Contract for Basic Market Data persistent storage (龙虎榜 / 研报 / 财报快照)."""

    @abstractmethod
    def upsert_longhu_rows(self, rows: list[dict[str, Any]]) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_longhu_rows(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def set_meta(self, key: str, value: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_meta(self, key: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_financial_stash(self, code: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def count_financial_stash_rows(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def insert_yanbao_batch(
        self, category: str, items: list[dict[str, Any]], batch_id: str
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_longhu_for_code(self, code: str, *, limit: int = 20) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def latest_longhu_trade_date(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def list_longhu_by_date(self, trade_date: str, *, limit: int = 500) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def list_longhu_latest_dates(self, limit: int = 20) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def list_yanbao(self, *, category: str | None = None, limit: int = 120) -> list[dict[str, Any]]:
        raise NotImplementedError


class UserRepository(ABC):
    """Port for user persistence (returns domain ``UserAccount``, not ORM models)."""

    @abstractmethod
    def get_by_id(self, user_id: str) -> UserAccount | None:
        """Get user by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_username(self, username: str) -> UserAccount | None:
        """Get user by username."""
        raise NotImplementedError

    @abstractmethod
    def create(self, user: UserAccount) -> str:
        """Create user and return ID."""
        raise NotImplementedError

    @abstractmethod
    def update(self, user_id: str, data: dict[str, Any]) -> bool:
        """Update user."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Delete user."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self, limit: int = 100) -> list[UserAccount]:
        raise NotImplementedError

    @abstractmethod
    def list_users(self) -> list[UserAccount]:
        raise NotImplementedError


class WatchlistRepository(ABC):
    """Port for watchlist persistence."""

    @abstractmethod
    def list_symbols(self, user_id: int = 1) -> list[str]:
        """List symbols in user's watchlist."""
        raise NotImplementedError

    @abstractmethod
    def add_symbol(self, symbol: str, user_id: int = 1) -> bool:
        """Add symbol to watchlist."""
        raise NotImplementedError

    @abstractmethod
    def remove_symbol(self, symbol: str, user_id: int = 1) -> bool:
        """Remove symbol from watchlist."""
        raise NotImplementedError

    @abstractmethod
    def save_symbols(self, user_id: int, symbols: list[str]) -> None:
        """Save all symbols for user (replace existing)."""
        raise NotImplementedError


class StockGroupRepository(ABC):
    """Port for stock group persistence - 支持用户隔离"""
    @abstractmethod
    def list_groups(self, user_id: int = 1) -> list[dict[str, Any]]:
        """List stock groups for a user."""
        raise NotImplementedError

    @abstractmethod
    def create_group(self, name: str, description: str = "", color: str = "", user_id: int = 1) -> dict | None:
        """Create stock group for a user."""
        raise NotImplementedError

    @abstractmethod
    def update_group(self, group_id: int, name: str, description: str = "", color: str = "", user_id: int = 1) -> bool:
        """Update stock group."""
        raise NotImplementedError

    @abstractmethod
    def delete_group(self, group_id: int, user_id: int = 1) -> bool:
        """Delete stock group."""
        raise NotImplementedError

    @abstractmethod
    def list_group_symbols(self, group_id: int, user_id: int = 1) -> list[str]:
        """List symbols in a group."""
        raise NotImplementedError

    @abstractmethod
    def add_symbol_to_group(self, group_id: int, symbol: str, user_id: int = 1) -> bool:
        """Add symbol to group."""
        raise NotImplementedError

    @abstractmethod
    def remove_symbol_from_group(self, group_id: int, symbol: str, user_id: int = 1) -> bool:
        """Remove symbol from group."""
        raise NotImplementedError

class PaymentRepository(ABC):
    """Port for payment persistence."""

    @abstractmethod
    def save_payment(self, payment: Any) -> str:
        """Save payment intent."""
        raise NotImplementedError

    @abstractmethod
    def get_payment(self, payment_id: str) -> Any | None:
        """Get payment by ID."""
        raise NotImplementedError

    @abstractmethod
    def update_payment_status(self, payment_id: str, status: str) -> bool:
        """Update payment status."""
        raise NotImplementedError


class PaymentGatewayPort(ABC):
    """Port for payment gateway integration."""

    @abstractmethod
    def create_payment_intent(self, amount: float, currency: str = "CNY") -> dict[str, Any]:
        """Create payment intent."""
        raise NotImplementedError

    @abstractmethod
    def process_payment(self, payment_id: str, payment_data: dict[str, Any]) -> dict[str, Any]:
        """Process payment."""
        raise NotImplementedError

    @abstractmethod
    def refund_payment(self, payment_id: str, amount: float | None = None) -> dict[str, Any]:
        """Refund payment."""
        raise NotImplementedError


__all__ = [
    "IBasicMarketDataRepository",
    "UserRepository",
    "WatchlistRepository",
    "StockGroupRepository",
    "PaymentRepository",
    "PaymentGatewayPort",
]
