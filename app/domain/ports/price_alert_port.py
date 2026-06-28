from __future__ import annotations

"""Port for user price alert storage."""

from abc import ABC, abstractmethod
from typing import Any


class PriceAlertRepository(ABC):
    @abstractmethod
    def get_alerts_for_symbol(self, symbol: str) -> list[Any]:
        raise NotImplementedError


class NullPriceAlertRepository(PriceAlertRepository):
    """No-op alerts backend (JSON store not yet wired)."""

    def get_alerts_for_symbol(self, symbol: str) -> list[Any]:
        return []
