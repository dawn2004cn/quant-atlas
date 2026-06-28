from __future__ import annotations
"""Repository factory helpers for SQLite/MySQL backends.

This module provides both sync and async repository factory functions.
Phase 41 migration introduces async versions that use SQLAlchemy AsyncSession
+ asyncmy for non-blocking I/O operations.

Sync factories (legacy):
    - create_user_repository()
    - create_watchlist_repository()
    - create_stock_group_repository()

Async factories (Phase 41):
    - create_async_user_repository()
    - create_async_watchlist_repository()
    - create_async_stock_group_repository()
"""


from pathlib import Path
from typing import Any

from ....config import AppSettings, INSTANCE_DIR
from ..mysql.mysql_repositories import (
    MySQLStockGroupRepository,
    MySQLUserRepository,
    MySQLWatchlistRepository,
)

# Lazy import for SQLite repos — these classes may not exist in environments
# that have not yet implemented the SQLite backend.
_SQLITE_IMPORT_ERROR = None
try:
    from ..sqlite.sqlite_repositories import (
        SQLiteStockGroupRepository,
        SQLiteUserRepository,
        SQLiteWatchlistRepository,
    )
except ImportError as _e:
    _SQLITE_IMPORT_ERROR = _e

from ..mysql.async_mysql_repositories import (
    AsyncMySQLUserRepository,
    AsyncMySQLWatchlistRepository,
    AsyncMySQLStockGroupRepository,
    AsyncMySQLSignalFlagPoolRepository,
    AsyncMySQLTradingRepository,
    AsyncMySQLInvestmentManagerRepository,
)
from ...database.async_mysql_client import create_async_session_factory


def create_stock_cache():
    """Process singleton local quote/history cache (infrastructure only)."""
    from app.infrastructure.database.stock_cache_db import StockCache

    return StockCache.default()


def create_sqlalchemy_session_factory(settings: AppSettings):
    """SQLAlchemy scoped session factory for MySQL-backed Celery tasks."""
    from app.infrastructure.database.orm import create_session_factory

    if not settings.use_mysql:
        raise RuntimeError("SQLAlchemy session factory requires MySQL backend")
    return create_session_factory(settings.database_uri)


def create_factor_repository(settings: AppSettings, session_factory=None):
    from app.infrastructure.repositories.factor_repository import FactorRepository

    if session_factory is None:
        session_factory = create_sqlalchemy_session_factory(settings)
    return FactorRepository(session_factory)


def create_execution_feedback_repository(settings: AppSettings, session_factory=None):
    from app.infrastructure.repositories.execution_feedback import ExecutionFeedbackRepository

    if session_factory is None:
        session_factory = create_sqlalchemy_session_factory(settings)
    return ExecutionFeedbackRepository(session_factory)


def create_slippage_analysis_service(settings: AppSettings, session_factory=None):
    from app.infrastructure.repositories.execution_feedback import SlippageAnalysisService

    repo = create_execution_feedback_repository(settings, session_factory)
    return SlippageAnalysisService(repo)


def create_stock_metadata_repository(settings: AppSettings):
    from ..mysql.mysql_stock_metadata_repository import (
        MySQLStockMetadataRepository,
        NullStockMetadataRepository,
    )

    if settings.use_mysql and settings.mysql:
        return MySQLStockMetadataRepository(settings.mysql)
    return NullStockMetadataRepository()


def create_mysql_connection_port(settings: AppSettings):
    from app.infrastructure.database.mysql_connection_adapter import (
        MySQLConnectionAdapter,
        NullMySQLConnectionPort,
    )

    if settings.use_mysql and settings.mysql:
        return MySQLConnectionAdapter(settings.mysql)
    return NullMySQLConnectionPort()


def create_tdx_gpcw_repository(settings: AppSettings):
    from ..mysql.mysql_tdx_gpcw_repository import (
        MySQLTdxGpcwRepository,
        NullTdxGpcwRepository,
    )

    if settings.use_mysql and settings.mysql:
        return MySQLTdxGpcwRepository(mysql=settings.mysql)
    return NullTdxGpcwRepository()


def create_default_qlib_pipeline_service():
    """Construct Qlib pipeline with the same dependencies as ``create_app``."""
    from app.modules.data.services.qlib_pipeline_service import QlibPipelineService
    from app.modules.system.services.tools.tool_facade_service import ToolFacadeService
    from app.config import BASE_DIR, get_settings
    from app.infrastructure.providers.market_data import MultiSourceMarketProvider

    s = get_settings()
    return QlibPipelineService(
        ToolFacadeService(MultiSourceMarketProvider(), None, None, None, None),
        base_dir=BASE_DIR,
        tdx_root_path=s.tdx_root_path,
        stock_cache=create_stock_cache(),
    )


def create_user_repository(settings: AppSettings, session_factory=None):
    if settings.use_mysql:
        if session_factory is None:
            raise RuntimeError("MySQL user repository requires SQLAlchemy session_factory")
        return MySQLUserRepository(
            session_factory,
            users_json_path=settings.user_store_path,
        )
    if _SQLITE_IMPORT_ERROR is not None:
        raise RuntimeError(
            "SQLite user repository is not available. "
            "Set DATABASE_BACKEND=mysql or install sqlite repositories. "
            f"Root cause: {_SQLITE_IMPORT_ERROR}"
        ) from _SQLITE_IMPORT_ERROR
    return SQLiteUserRepository(
        settings.sqlite_path,
        users_json_path=settings.user_store_path,
    )


def create_watchlist_repository(settings: AppSettings, session_factory=None):
    if settings.use_mysql:
        if session_factory is None:
            raise RuntimeError("MySQL watchlist repository requires SQLAlchemy session_factory")
        return MySQLWatchlistRepository(
            session_factory,
            watchlist_json_path=settings.watchlist_store_path,
        )
    if _SQLITE_IMPORT_ERROR is not None:
        raise RuntimeError(
            "SQLite watchlist repository is not available. "
            "Set DATABASE_BACKEND=mysql or install sqlite repositories. "
            f"Root cause: {_SQLITE_IMPORT_ERROR}"
        ) from _SQLITE_IMPORT_ERROR
    return SQLiteWatchlistRepository(
        settings.sqlite_path,
        watchlist_json_path=settings.watchlist_store_path,
    )


def create_stock_group_repository(settings: AppSettings, session_factory=None):
    if settings.use_mysql:
        if session_factory is None:
            raise RuntimeError("MySQL stock-group repository requires SQLAlchemy session_factory")
        return MySQLStockGroupRepository(
            session_factory,
            stock_groups_json_path=settings.stock_groups_store_path,
        )
    if _SQLITE_IMPORT_ERROR is not None:
        raise RuntimeError(
            "SQLite stock-group repository is not available. "
            "Set DATABASE_BACKEND=mysql or install sqlite repositories. "
            f"Root cause: {_SQLITE_IMPORT_ERROR}"
        ) from _SQLITE_IMPORT_ERROR
    return SQLiteStockGroupRepository(
        settings.sqlite_path,
        stock_groups_json_path=settings.stock_groups_store_path,
    )


def create_news_archive_repository(settings: AppSettings, session_factory=None):
    from .facades.news_archive_repository import NewsArchiveRepository

    if settings.use_mysql:
        return NewsArchiveRepository(mysql=settings.mysql, session_factory=session_factory)
    return NewsArchiveRepository(db_path=INSTANCE_DIR / "news_archive.db")


def create_signal_flag_pool_repository(settings: AppSettings, session_factory=None):
    from .facades.signal_flag_pool_repository import SignalFlagPoolRepository

    if settings.use_mysql:
        return SignalFlagPoolRepository(mysql=settings.mysql, session_factory=session_factory)
    return SignalFlagPoolRepository(
        db_path=Path(settings.sqlite_path).parent / "signal_flag_pool.db"
    )


def create_basic_market_data_repository(settings: AppSettings, session_factory=None):
    from .facades.basic_market_data_repository import BasicMarketDataRepository

    if settings.use_mysql:
        return BasicMarketDataRepository(mysql=settings.mysql, session_factory=session_factory)
    return BasicMarketDataRepository(
        db_path=Path(settings.sqlite_path).parent / "basic_market_data.db"
    )


def create_investment_manager_repository(settings: AppSettings, session_factory=None):
    from .facades.investment_manager_repository import InvestmentManagerRepository

    if settings.use_mysql:
        return InvestmentManagerRepository(db_path=Path(settings.sqlite_path).parent / "investment_managers.db")
    return InvestmentManagerRepository(
        db_path=Path(settings.sqlite_path).parent / "investment_managers.db"
    )


def create_moments_repository(settings: AppSettings, session_factory=None):
    from .facades.moments_repository import MomentsRepository

    if settings.use_mysql:
        return MomentsRepository(mysql=settings.mysql, session_factory=session_factory)
    return MomentsRepository(db_path=Path(settings.sqlite_path).parent / "moments.db")


def create_analysis_report_repository(settings: AppSettings, session_factory=None):
    from .facades.analysis_report_repository import AnalysisReportRepository

    if settings.use_mysql:
        return AnalysisReportRepository(mysql=settings.mysql, session_factory=session_factory)
    return AnalysisReportRepository(
        sqlite_path=Path(settings.sqlite_path).parent / "analysis_reports.db"
    )


def create_signal_observation_repository(session_factory) -> Any | None:
    """Build MySQL signal observation repo from scoped session factory; None if unavailable."""
    if session_factory is None:
        return None
    try:
        from ..mysql.mysql_signal_observation_repository import MySQLSignalObservationRepository

        repo = MySQLSignalObservationRepository(session_factory())
        return repo
    except Exception:
        return None


def create_async_user_repository(database_uri: str) -> AsyncMySQLUserRepository:
    """Create async User repository (Phase 41).

    This replaces the sync MySQLUserRepository with an async version
    that uses SQLAlchemy AsyncSession + asyncmy for non-blocking I/O.

    Args:
        database_uri: SQLAlchemy database URI (e.g., mysql+pymysql://...)

    Returns:
        AsyncMySQLUserRepository instance

    Example:
        repo = create_async_user_repository(settings.database_uri)
        users = await repo.list_users()  # Non-blocking!
    """
    session_factory = create_async_session_factory(database_uri)
    return AsyncMySQLUserRepository(session_factory)


def create_async_watchlist_repository(database_uri: str) -> AsyncMySQLWatchlistRepository:
    """Create async Watchlist repository (Phase 41).

    Args:
        database_uri: SQLAlchemy database URI

    Returns:
        AsyncMySQLWatchlistRepository instance
    """
    session_factory = create_async_session_factory(database_uri)
    return AsyncMySQLWatchlistRepository(session_factory)


def create_async_stock_group_repository(database_uri: str) -> AsyncMySQLStockGroupRepository:
    """Create async StockGroup repository (Phase 41).

    Args:
        database_uri: SQLAlchemy database URI

    Returns:
        AsyncMySQLStockGroupRepository instance
    """
    session_factory = create_async_session_factory(database_uri)
    return AsyncMySQLStockGroupRepository(session_factory)


def create_async_repositories(settings: AppSettings) -> dict:
    """Factory to create all async repositories (Phase 41).

    This is the main entry point for async repository creation.
    Use this in combination with the sync version for gradual migration.

    Args:
        settings: Application settings with database configuration

    Returns:
        Dictionary of async repository instances

    Example:
        async_repos = create_async_repositories(settings)
        user_repo = async_repos['user_repository']
        users = await user_repo.list_users()
    """
    if not settings.use_mysql:
        raise RuntimeError("Async repositories require MySQL backend")

    return {
        "user_repository": create_async_user_repository(settings.database_uri),
        "watchlist_repository": create_async_watchlist_repository(settings.database_uri),
        "stock_group_repository": create_async_stock_group_repository(settings.database_uri),
        "signal_flag_pool_repository": create_async_signal_flag_pool_repository(settings.database_uri),
        "trading_repository": create_async_trading_repository(settings.database_uri),
        "investment_manager_repository": create_async_investment_manager_repository(settings.database_uri),
    }


def create_async_signal_flag_pool_repository(database_uri: str) -> AsyncMySQLSignalFlagPoolRepository:
    """Create async SignalFlagPool repository (Phase 41)."""
    session_factory = create_async_session_factory(database_uri)
    return AsyncMySQLSignalFlagPoolRepository(session_factory)


def create_async_trading_repository(database_uri: str) -> AsyncMySQLTradingRepository:
    """Create async Trading repository (Phase 41)."""
    session_factory = create_async_session_factory(database_uri)
    return AsyncMySQLTradingRepository(session_factory)


def create_async_investment_manager_repository(database_uri: str) -> AsyncMySQLInvestmentManagerRepository:
    """Create async InvestmentManager repository (Phase 41)."""
    session_factory = create_async_session_factory(database_uri)
    return AsyncMySQLInvestmentManagerRepository(session_factory)


def create_postgres_connection_port(settings: AppSettings):
    from app.infrastructure.database.postgres_connection_adapter import (
        NullPostgresConnectionPort,
        PostgresConnectionAdapter,
    )

    if settings.postgres is not None and settings.use_timescaledb:
        return PostgresConnectionAdapter(settings.postgres)
    return NullPostgresConnectionPort()


def create_timescale_bar_repository(settings: AppSettings):
    from ..postgres.postgres_timescale_bar_repository import (
        NullPostgresTimescaleBarRepository,
        PostgresTimescaleBarRepository,
    )

    if settings.postgres is not None and settings.use_timescaledb:
        return PostgresTimescaleBarRepository(settings.postgres)
    return NullPostgresTimescaleBarRepository()


def create_hot_sector_repository(settings: AppSettings):
    """Hot-sector snapshot repository; Null impl when MySQL is disabled."""
    if settings.use_mysql and settings.mysql is not None:
        from ..mysql.mysql_hot_sector_repository import MySQLHotSectorRepository

        return MySQLHotSectorRepository(settings.mysql)
    from ..mysql.null_hot_sector_repository import NullHotSectorStorageRepository

    return NullHotSectorStorageRepository()


def create_tdx_dayk_repository(settings: AppSettings):
    if not settings.use_mysql or settings.mysql is None:
        return None
    from ..mysql.mysql_tdx_dayk_repository import MySQLTdxDaykRepository

    return MySQLTdxDaykRepository(settings.mysql)


class _TimescaleOnlyQlibStub:
    """Timescale-only TDX sync：不触发 qlib bootstrap。"""

    def __init__(self, base_dir: Path) -> None:
        self.export_dir = Path(base_dir) / "instance" / "qlib_export"


def create_tdx_dayk_sync_service(*, base_dir=None, require_qlib: bool = True):
    """TDX 日 K 同步服务（Celery / API / 脚本统一入口）。"""
    from pathlib import Path

    from app.modules.data.services.tdx_dayk_sync_service import TdxDaykSyncService
    from app.config import BASE_DIR, get_settings

    root = Path(base_dir) if base_dir is not None else BASE_DIR
    settings = get_settings()
    qlib = (
        create_default_qlib_pipeline_service()
        if require_qlib
        else _TimescaleOnlyQlibStub(root)
    )
    return TdxDaykSyncService(
        settings=settings,
        qlib_pipeline=qlib,
        base_dir=root,
    )


def create_tdx_base_data_repository(settings: AppSettings):
    if not settings.use_mysql or settings.mysql is None:
        return None
    from ..mysql.mysql_tdx_base_data_repository import MySQLTdxBaseDataRepository

    return MySQLTdxBaseDataRepository(settings.mysql)


def create_tdx_block_repository(settings: AppSettings):
    """MySQL TDX block read repository; None when MySQL is disabled."""
    if not settings.use_mysql or settings.mysql is None:
        return None
    from ..mysql.mysql_tdx_block_repository import MySQLTdxBlockRepository
    return MySQLTdxBlockRepository(settings.mysql)

def create_collaboration_repository(settings, session_factory=None):
    """Create CollaborationRepository with fallback to JSON if MySQL unavailable."""
    from pathlib import Path
    if settings.use_mysql and session_factory is not None:
        try:
            from ..mysql.mysql_collaboration_repository import MySQLCollaborationRepository
            return MySQLCollaborationRepository(session_factory())
        except Exception:
            pass
    from app.infrastructure.repositories.common.json_repositories import JsonCollaborationRepository
    return JsonCollaborationRepository(Path(settings.sqlite_path).parent / "collaboration.json")


def create_integration_probe_repository(settings: AppSettings):
    if not settings.use_mysql or settings.mysql is None:
        return None
    from ..mysql.mysql_integration_probe_repository import MySQLIntegrationProbeRepository

    return MySQLIntegrationProbeRepository(settings.mysql)
