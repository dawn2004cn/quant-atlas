from __future__ import annotations
"""Factor repository port for domain layer.

Defines the interface that factor-related operations use to interact
with persistence. Infrastructure provides the concrete implementation.
"""

from abc import ABC, abstractmethod
from typing import Any


class FactorRepositoryPort(ABC):
    """Port for factor persistence operations."""

    @abstractmethod
    async def create_factor(self, factor_data: dict[str, Any]) -> str:
        """Create a new factor record. Returns factor_id."""
        raise NotImplementedError

    @abstractmethod
    async def get_factor(self, factor_id: str) -> dict[str, Any] | None:
        """Get a factor by ID, or None."""
        raise NotImplementedError

    @abstractmethod
    async def list_factors(
        self,
        *,
        category: str | None = None,
        status: str = "active",
        order_by: str = "ir",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List factors with optional filters."""
        raise NotImplementedError

    @abstractmethod
    async def update_factor_performance(
        self,
        *,
        factor_id: str,
        ic_mean: float,
        ic_std: float,
        ir: float,
        decay_rate: float,
    ) -> None:
        """Update factor performance metrics."""
        raise NotImplementedError

    @abstractmethod
    async def deactivate_factor(self, factor_id: str, reason: str = "") -> bool:
        """Deactivate a factor."""
        raise NotImplementedError

    @abstractmethod
    async def add_ic_record(
        self,
        *,
        factor_id: str,
        calc_date: str,
        ic_value: float,
        sample_count: int = 100,
    ) -> None:
        """Add an IC history record."""
        raise NotImplementedError

    @abstractmethod
    async def get_ic_history(
        self,
        factor_id: str,
        *,
        days: int = 60,
    ) -> list[dict[str, Any]]:
        """Get IC history for a factor."""
        raise NotImplementedError

    @abstractmethod
    async def get_top_factors(
        self,
        *,
        limit: int = 20,
        min_ir: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Get top-ranked factors by IR."""
        raise NotImplementedError

    @abstractmethod
    async def log_decay_event(
        self,
        *,
        factor_id: str,
        detection_date: str,
        ic_mean_current: float,
        ic_mean_historical: float,
        decay_ratio: float,
        severity: str,
    ) -> None:
        """Log a factor decay detection event."""
        raise NotImplementedError
