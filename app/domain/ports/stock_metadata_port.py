from __future__ import annotations

"""Port for ``base_stock_reference`` fundamental metadata."""

from abc import ABC, abstractmethod
from typing import Any


class StockMetadataRepository(ABC):
    """Read-only stock reference metadata (name, industry, region, etc.)."""

    @abstractmethod
    def get_basic_info(self, code: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_batch(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def enrich_stock_list(self, stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError
