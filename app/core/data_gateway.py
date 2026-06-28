"""
DataGateway — unified data access layer.

Eliminates the 75+ callers that currently import from scattered repo paths.
All data access goes through ``DataGateway``, which dispatches to the right
backend (MySQL / SQLite / PostgreSQL) via ``RepositoryRegistry``.

Usage::

    from app.core.data_gateway import DataGateway

    gw = DataGateway(settings)
    pool = gw.signal_flag_pool
    pool.replace_pool("2025-01-01", rows)

Pattern::

    DataGateway
      ├── .signal_flag_pool     → SignalFlagPoolRepository
      ├── .user                 → UserRepository
      ├── .watchlist            → WatchlistRepository
      ├── .stock_group          → StockGroupRepository
      ├── .news_archive         → NewsArchiveRepository
      ├── .basic_market_data    → BasicMarketDataRepository
      ├── .investment_manager   → InvestmentManagerRepository
      ├── .moments              → MomentsRepository
      ├── .analysis_report      → AnalysisReportRepository
      ├── .factor_vault         → FactorVault (MySQL only)
      ├── .execution_feedback   → ExecutionFeedbackRepository
      └── .hot_sector           → HotSectorRepository / Null

Lazy initialization — repos are created on first access and cached.
"""

from __future__ import annotations

from typing import Any

from app.config import AppSettings
from app.core.logger import get_logger

logger = get_logger(__name__)


class DataGateway:
    """Unified entry point for all database repositories."""

    def __init__(
        self,
        settings: AppSettings,
        session_factory: Any = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._use_mysql = bool(getattr(settings, "use_mysql", False))
        self._mysql_cfg = getattr(settings, "mysql", None)
        self._cache: dict[str, Any] = {}

    def _repo(self, name: str, factory: Any, *args: Any, **kwargs: Any) -> Any:
        if name not in self._cache:
            try:
                self._cache[name] = factory(*args, **kwargs)
            except Exception as exc:
                logger.warning("DataGateway[%s] init failed: %s", name, exc)
                self._cache[name] = None
        return self._cache[name]

    # ----- Facade-style repos (SQLite ↔ MySQL) -----

    @property
    def signal_flag_pool(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_signal_flag_pool_repository
        return self._repo("signal_flag_pool", create_signal_flag_pool_repository, self._settings)

    @property
    def news_archive(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_news_archive_repository
        return self._repo("news_archive", create_news_archive_repository, self._settings)

    @property
    def basic_market_data(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_basic_market_data_repository
        return self._repo("basic_market_data", create_basic_market_data_repository, self._settings)

    @property
    def investment_manager(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_investment_manager_repository
        return self._repo("investment_manager", create_investment_manager_repository, self._settings)

    @property
    def moments(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_moments_repository
        return self._repo("moments", create_moments_repository, self._settings)

    @property
    def analysis_report(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_analysis_report_repository
        return self._repo("analysis_report", create_analysis_report_repository, self._settings)

    # ----- MySQL-only repos -----

    @property
    def user(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_user_repository
        return self._repo("user", create_user_repository, self._settings, session_factory=self._session_factory)

    @property
    def watchlist(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_watchlist_repository
        return self._repo("watchlist", create_watchlist_repository, self._settings, session_factory=self._session_factory)

    @property
    def stock_group(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_stock_group_repository
        return self._repo("stock_group", create_stock_group_repository, self._settings, session_factory=self._session_factory)

    @property
    def factor_vault(self) -> Any:
        if not self._use_mysql:
            return None
        from app.infrastructure.repositories.mysql.mysql_factor_vault import MySQLFactorVault
        return self._repo("factor_vault", MySQLFactorVault)

    @property
    def hot_sector(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_hot_sector_repository
        return self._repo("hot_sector", create_hot_sector_repository, self._settings)

    @property
    def stock_metadata(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_stock_metadata_repository
        return self._repo("stock_metadata", create_stock_metadata_repository, self._settings)

    # ----- Helpers -----

    @property
    def stock_cache(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_stock_cache
        return self._repo("stock_cache", create_stock_cache)

    @property
    def signal_observation(self) -> Any:
        return self._repo("signal_observation", lambda: self._signal_observation_factory())

    def _signal_observation_factory(self) -> Any:
        from app.infrastructure.repositories.common.deps import create_signal_observation_repository
        return create_signal_observation_repository(self._session_factory)

    def close(self) -> None:
        """Release all cached repository instances."""
        self._cache.clear()
