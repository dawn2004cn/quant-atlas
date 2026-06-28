from __future__ import annotations
"""Repository Registry - Central registry for all domain repositories.

Provides a unified interface for creating and accessing repositories.
"""



from app.domain.repositories.stock import IStockRepository, IMarketDataRepository
from app.domain.repositories.signal import ISignalRepository
from app.domain.ports.repository_ports import UserRepository, WatchlistRepository


from app.core.logger import get_logger

logger = get_logger(__name__)


class RepositoryRegistry:
    """Central registry for all repositories."""

    _instance: RepositoryRegistry | None = None
    _repositories: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._repositories = {}
        return cls._instance

    def register(self, name: str, repo: any) -> None:
        """Register a repository."""
        self._repositories[name] = repo
        logger.info(f"Registered repository: {name}")

    def get(self, name: str) -> any | None:
        """Get a registered repository."""
        return self._repositories.get(name)

    def get_stock_repo(self) -> IStockRepository | None:
        """Get stock repository."""
        return self._repositories.get("stock")

    def get_signal_repo(self) -> ISignalRepository | None:
        """Get signal repository."""
        return self._repositories.get("signal")

    def get_market_data_repo(self) -> IMarketDataRepository | None:
        """Get market data repository."""
        return self._repositories.get("market_data")

    def get_user_repo(self) -> UserRepository | None:
        """Get user repository."""
        return self._repositories.get("user")

    def get_watchlist_repo(self) -> WatchlistRepository | None:
        """Get watchlist repository."""
        return self._repositories.get("watchlist")

    def clear(self) -> None:
        """Clear all repositories (for testing)."""
        self._repositories.clear()


def create_repositories(session_factory) -> dict:
    """Create all repositories and register them."""
    from app.infrastructure.repositories.stock_repository import MySQLStockRepository, MySQLMarketDataRepository
    from app.infrastructure.repositories.signal_repository import MySQLSignalRepository
    from app.infrastructure.repositories.mysql_repositories import MySQLUserRepository, MySQLWatchlistRepository, MySQLStockGroupRepository
    from app.infrastructure.repositories.investment_manager_repository import InvestmentManagerRepository
    from app.infrastructure.repositories.basic_market_data_repository import BasicMarketDataRepository
    from app.infrastructure.repositories.news_archive_repository import NewsArchiveRepository
    from app.infrastructure.repositories.signal_flag_pool_repository import SignalFlagPoolRepository

    registry = RepositoryRegistry()

    # Initialize repositories
    user_repo = MySQLUserRepository(session_factory)
    watchlist_repo = MySQLWatchlistRepository(session_factory)
    stock_group_repo = MySQLStockGroupRepository(session_factory)
    signal_repo = MySQLSignalRepository(session_factory)
    stock_repo = MySQLStockRepository(session_factory)
    market_data_repo = MySQLMarketDataRepository(session_factory)
    investment_manager_repo = InvestmentManagerRepository(session_factory=session_factory)
    basic_market_data_repo = BasicMarketDataRepository(session_factory=session_factory)
    news_archive_repo = NewsArchiveRepository(session_factory=session_factory)
    signal_flag_pool_repo = SignalFlagPoolRepository(session_factory=session_factory)

    registry.register("user", user_repo)
    registry.register("watchlist", watchlist_repo)
    registry.register("stock_group", stock_group_repo)
    registry.register("signal", signal_repo)
    registry.register("stock", stock_repo)
    registry.register("market_data", market_data_repo)
    registry.register("investment_manager", investment_manager_repo)
    registry.register("basic_market_data", basic_market_data_repo)
    registry.register("news_archive", news_archive_repo)
    registry.register("signal_flag_pool", signal_flag_pool_repo)

    return {
        "user": user_repo,
        "watchlist": watchlist_repo,
        "stock_group": stock_group_repo,
        "signal": signal_repo,
        "stock": stock_repo,
        "market_data": market_data_repo,
        "investment_manager": investment_manager_repo,
        "basic_market_data": basic_market_data_repo,
        "news_archive": news_archive_repo,
        "signal_flag_pool": signal_flag_pool_repo,
    }

__all__ = ["RepositoryRegistry", "create_repositories"]
