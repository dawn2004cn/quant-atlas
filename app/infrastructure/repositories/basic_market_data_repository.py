"""Basic Market Data Repository — re-exports SQLite implementation.

Replaces broken facade chain (basic->facade->basic = circular).
"""
from app.infrastructure.repositories.sqlite.sqlite_basic_market_data_repository import (
    SQLiteBasicMarketDataRepository as BasicMarketDataRepository,
)

__all__ = ["BasicMarketDataRepository"]
