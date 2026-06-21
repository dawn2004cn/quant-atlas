"""Shared kernel value objects used across multiple bounded contexts.

StockQuote and UserAccount are referenced by 5+ modules each,
making them natural candidates for the shared kernel.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import MarketCode


@dataclass(frozen=True)
class StockQuote:
    """Realtime quote model."""

    code: str
    name: str
    market: MarketCode
    price: float
    change_pct: float
    volume: float = 0.0
    amount: float = 0.0
    turnover: float = 0.0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    source: str = "unknown"
    updated_at: str | None = None
    change_amount: float = 0.0
    prev_close: float = 0.0
    volume_ratio: float = 0.0
    amplitude: float = 0.0
    pe: float = 0.0
    pb: float = 0.0
    total_market_cap: float = 0.0
    industry: str = ""

    def validate(self) -> None:
        """Domain invariant check."""
        if self.price < 0:
            raise ValueError(f"Stock {self.code} price cannot be negative: {self.price}")
        if self.volume < 0:
            raise ValueError(f"Stock {self.code} volume cannot be negative: {self.volume}")

    @property
    def is_up(self) -> bool:
        return self.change_pct > 0

    @property
    def is_down(self) -> bool:
        return self.change_pct < 0


@dataclass(frozen=True)
class UserAccount:
    """User aggregate."""

    user_id: int
    username: str
    role: str
    password_hash: str
    avatar_url: str = ""

    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    def is_admin(self) -> bool:
        return self.role == "admin"

    def can_manage_users(self) -> bool:
        return self.role in ("admin", "manager")

    def display_name(self) -> str:
        return self.username or f"User({self.user_id})"
