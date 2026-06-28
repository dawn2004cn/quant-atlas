from __future__ import annotations

"""Port for news archive persistence."""

from abc import ABC, abstractmethod
from typing import Any


class NewsArchiveRepository(ABC):
    """Contract for per-symbol news snapshot archive."""

    @abstractmethod
    def latest_fetched_at(self, market: str, symbol: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def get_meta(self, market: str, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def upsert_meta(
        self, market: str, symbol: str, *, company_name: str, industry_hint: str
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def ingest_snapshot(self, market: str, symbol: str, snapshot: dict[str, Any]) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_for_symbol(
        self, market: str, symbol: str, *, limit: int = 80
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
