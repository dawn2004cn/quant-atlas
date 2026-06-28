from __future__ import annotations

"""Port for signal-flag scan pool persistence."""

from abc import ABC, abstractmethod
from typing import Any


class SignalFlagPoolRepository(ABC):
    """Contract for daily signal-flag candidate pool storage."""

    @abstractmethod
    def list_dates(self, *, limit: int = 120) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_pool(self, pool_date: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def replace_pool(self, pool_date: str, rows: list[dict[str, Any]]) -> int:
        raise NotImplementedError
