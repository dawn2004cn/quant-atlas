from __future__ import annotations

"""Stock Cache - Facade combining all repositories.

This module provides backward-compatible StockCache while using
decoupled repositories internally (Bridge Pattern + Single Responsibility).
"""


import threading
from typing import Any

from .adapters import create_database_adapter
from .history_repository import HistoryRepository
from .sentiment_repository import SentimentRepository
from .stock_repository import StockRepository


class StockCache:
    """Facade for stock data access - combines all repositories.

    This maintains backward compatibility while internally using
    decoupled repositories.
    """

    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._init_lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str | None = None):
        if hasattr(self, "initialized"):
            return
        self._adapter = create_database_adapter()
        self._stock_repo = StockRepository(self._adapter)
        self._history_repo = HistoryRepository(self._adapter)
        self._sentiment_repo = SentimentRepository(self._adapter)
        self.initialized = True
        self.db_path = getattr(self._adapter, "_db_path", "memory")

    @classmethod
    def default(cls):
        return cls()

    def save_stocks(self, stocks_data: list[dict[str, Any]]) -> None:
        """Save or update stocks."""
        self._stock_repo.save_stocks(stocks_data)

    def get_all_stocks(self, max_age_minutes: int = 1440) -> list[dict[str, Any]]:
        """Get all stocks."""
        return self._stock_repo.get_all_stocks(max_age_minutes)

    def list_all_codes(self) -> list[str]:
        """List all stock codes."""
        return self._stock_repo.list_all_codes()

    def get_stocks_by_codes(self, codes: list[str]) -> list[dict[str, Any]]:
        """Get stocks by codes."""
        return self._stock_repo.get_stocks_by_codes(codes)

    def list_stocks_for_admin(self, limit: int = 8000) -> list[dict[str, Any]]:
        """List stocks for admin."""
        return self._stock_repo.list_stocks_for_admin(limit)

    def stock_cache_admin_stats(self) -> dict[str, Any]:
        """Get admin statistics."""
        stock_count = self._stock_repo.get_stock_count()
        history_bar_count = self._history_repo.get_history_bar_count()
        latest_update = self._adapter.execute_scalar("SELECT MAX(update_time) FROM stocks")
        return {
            "stock_count": stock_count,
            "history_bar_count": history_bar_count,
            "latest_update": latest_update if latest_update else "-",
            "db_path": getattr(self._adapter, "_db_path", "unknown"),
        }

    def save_stock_history(self, stock_code: str, history: list[dict[str, Any]]) -> None:
        """Save stock history."""
        self._history_repo.save_history(stock_code, history)

    def get_stock_history(self, stock_code: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Get stock history by date range."""
        return self._history_repo.get_history(stock_code, start_date, end_date)

    def get_stock_history_for_code(self, stock_code: str, *, limit: int = 1000) -> list[dict[str, Any]]:
        """Get latest history for a stock."""
        return self._history_repo.get_history_latest(stock_code, limit)

    def save_sentiment(self, market: str, up_count: int, down_count: int, flat_count: int) -> None:
        """Save market sentiment."""
        self._sentiment_repo.save_sentiment(market, up_count, down_count, flat_count)

    def save_sentiment_daily(self, market: str, trade_date: str, up_count: int, down_count: int, flat_count: int) -> None:
        """Save daily market sentiment."""
        self._sentiment_repo.save_sentiment_daily(market, trade_date, up_count, down_count, flat_count)

    def get_latest_sentiment(self, market: str) -> dict[str, Any] | None:
        """Get latest sentiment."""
        return self._sentiment_repo.get_latest_sentiment(market)

    def get_sentiment_for_trade_date(self, market: str, trade_date: str) -> dict[str, Any] | None:
        """Get sentiment for trade date."""
        return self._sentiment_repo.get_sentiment_for_trade_date(market, trade_date)
