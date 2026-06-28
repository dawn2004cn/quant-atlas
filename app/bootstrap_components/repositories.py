"""Repositories configuration."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def create_repositories(settings: Any, session_factory: Any = None, **kwargs) -> Any:
    """Create repositories bundle."""
    from ..infrastructure.repositories.mysql_stockgroup_repository import MySQLStockGroupRepository
    from ..infrastructure.repositories.mysql_user_repository import MySQLUserRepository
    from ..infrastructure.repositories.mysql_watchlist_repository import MySQLWatchlistRepository
    from ..infrastructure.repositories.signal_repository import MySQLSignalRepository
    from ..infrastructure.repositories.stock_repository import MySQLMarketDataRepository, MySQLStockRepository

    class Repositories:
        user_repository = None
        watchlist_repository = None
        stock_group_repository = None
        stock_repository = None
        market_data_repository = None
        signal_repository = None
        news_archive_repository = None

        def __init__(self):
            if session_factory:
                try:
                    self.user_repository = MySQLUserRepository(session_factory)
                    self.watchlist_repository = MySQLWatchlistRepository(session_factory)
                    self.stock_group_repository = MySQLStockGroupRepository(session_factory)
                    self.stock_repository = MySQLStockRepository(session_factory)
                    self.market_data_repository = MySQLMarketDataRepository(session_factory)
                    self.signal_repository = MySQLSignalRepository(session_factory)
                except Exception as e:
                    logger.warning("Failed to initialize repositories: %s", e, exc_info=True)

    return Repositories()
