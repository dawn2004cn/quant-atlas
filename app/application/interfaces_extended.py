from __future__ import annotations
"""Extended Application Service Interfaces.

Additional interfaces for grouped services.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PortfolioPositionDTO:
    """Portfolio position."""
    stock_code: str
    quantity: int
    avg_cost: float
    current_price: float
    pnl: float
    weight: float


@dataclass
class MarketDataDTO:
    """Market data."""
    code: str
    name: str
    price: float
    change: float
    volume: int
    timestamp: str


@dataclass
class UserProfileDTO:
    """User profile."""
    user_id: str
    username: str
    role: str
    preferences: dict


# =============================================================================
# Portfolio Service Interface
# =============================================================================

class IPortfolioService(ABC):
    """Portfolio service interface."""

    @abstractmethod
    def get_positions(self, user_id: str) -> list[PortfolioPositionDTO]:
        """Get portfolio positions."""
        pass

    @abstractmethod
    def get_performance(self, user_id: str) -> dict:
        """Get portfolio performance."""
        pass

    @abstractmethod
    def calculate_risk_metrics(self, user_id: str) -> dict:
        """Calculate risk metrics."""
        pass


# =============================================================================
# Market Data Service Interface
# =============================================================================

class IMarketDataService(ABC):
    """Market data service interface."""

    @abstractmethod
    def get_quote(self, code: str) -> MarketDataDTO | None:
        """Get real-time quote."""
        pass

    @abstractmethod
    def get_history(self, code: str, days: int) -> list[MarketDataDTO]:
        """Get historical data."""
        pass

    @abstractmethod
    def subscribe_realtime(self, codes: list[str]) -> bool:
        """Subscribe to real-time updates."""
        pass


# =============================================================================
# User Service Interface
# =============================================================================

class IUserService(ABC):
    """User service interface."""

    @abstractmethod
    def get_profile(self, user_id: str) -> UserProfileDTO | None:
        """Get user profile."""
        pass

    @abstractmethod
    def update_preferences(self, user_id: str, preferences: dict) -> bool:
        """Update user preferences."""
        pass

    @abstractmethod
    def authenticate(self, username: str, password: str) -> str | None:
        """Authenticate user."""
        pass


__all__ = [
    "PortfolioPositionDTO",
    "MarketDataDTO",
    "UserProfileDTO",
    "IPortfolioService",
    "IMarketDataService",
    "IUserService",
]
