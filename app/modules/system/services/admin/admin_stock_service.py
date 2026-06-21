from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Admin Stock Service - wraps StockCache for admin operations."""


from typing import Any

from app.domain.ports.stock_cache_port import StockCachePort
from app.core.base_service import BaseApplicationService


class AdminStockService(BaseApplicationService):
    """Service for admin stock cache operations.

    Provides a cleaner interface than directly using StockCache.
    """

    def __init__(self, stock_cache: StockCachePort):
        super().__init__()
        self._cache = stock_cache

    def get_all_stocks(self, max_age_minutes: int = 1440) -> list[dict[str, Any]]:
        """Get all stocks with optional freshness filter."""
        self.logger.info("Fetching all stocks.")
        return self._cache.get_all_stocks(max_age_minutes)

    def get_stocks_paginated(self, offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Get stocks with pagination."""
        self.logger.info("Fetching paginated stocks.")
        all_stocks = self._cache.list_stocks_for_admin(limit=limit + offset)
        return all_stocks[offset:offset + limit]

    def get_stock_count(self) -> int:
        """Get total stock count."""
        self.logger.info("Fetching stock count.")
        stats = self._cache.stock_cache_admin_stats()
        return stats.get("stock_count", 0)

    def get_stats(self) -> GenericResponseDTO:
        """Get admin statistics."""
        self.logger.info("Fetching admin statistics.")
        return self._cache.stock_cache_admin_stats()

    def search_stocks(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search stocks by name or code."""
        self.logger.info(f"Searching stocks with keyword: {keyword}")
        all_stocks = self._cache.list_stocks_for_admin(limit=10000)
        keyword_lower = keyword.lower()
        results = [
            s for s in all_stocks
            if keyword_lower in s.get("code", "").lower()
            or keyword_lower in s.get("name", "").lower()
        ]
        return results[:limit]


# Singleton instance
_admin_stock_service: AdminStockService | None = None
_admin_stock_cache: StockCachePort | None = None


def configure_admin_stock_service(stock_cache: StockCachePort) -> None:
    global _admin_stock_cache, _admin_stock_service
    _admin_stock_cache = stock_cache
    _admin_stock_service = None


def get_admin_stock_service() -> AdminStockService:
    """Get singleton AdminStockService."""
    global _admin_stock_service
    if _admin_stock_service is None:
        if _admin_stock_cache is None:
            raise RuntimeError("AdminStockService requires configure_admin_stock_service() at bootstrap")
        _admin_stock_service = AdminStockService(_admin_stock_cache)
    return _admin_stock_service
