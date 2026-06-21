"""Repository registration - registers all implementations with the factory.

Registration is deferred to avoid circular imports when MySQL module files
import from ``app.infrastructure.repositories.factory``.
"""

from .factory import RepositoryRegistry, RepositoryType


_REGISTERED = False


def _register_all():
    """Register all repository implementations (called once, lazily)."""
    global _REGISTERED
    if _REGISTERED:
        return
    from ..mysql.mysql_investment_manager_repository import MySQLInvestmentManagerRepository
    from ..mysql.mysql_basic_market_data_repository import MySQLBasicMarketDataRepository
    from ..mysql.mysql_news_archive_repository import MySQLNewsArchiveRepository
    from ..mysql.mysql_signal_flag_pool_repository import MySQLSignalFlagPoolRepository
    from ..mysql.mysql_moments_repository import MySQLMomentsRepository
    from ..mysql.mysql_analysis_report_repository import MySQLAnalysisReportRepository
    from ..mysql.mysql_agent_repository import MySQLAgentRepository
    from ..mysql.mysql_trading_repository import MySQLTradingRepository
    from ..mysql.mysql_payment_repository import MySQLPaymentRepository
    from ..mysql.mysql_kronos_repository import MySQLKronosRepository
    from ..mysql.mysql_openbb_repository import MySQLOpenBBRepository
    from ..mysql.mysql_quantml_repository import MySQLQuantMLFactorRepository

    from ..sqlite.sqlite_investment_manager_repository import SQLiteInvestmentManagerRepository
    from ..sqlite.sqlite_basic_market_data_repository import SQLiteBasicMarketDataRepository
    from ..sqlite.sqlite_news_archive_repository import SQLiteNewsArchiveRepository
    from ..sqlite.sqlite_signal_flag_pool_repository import SQLiteSignalFlagPoolRepository
    from ..sqlite.sqlite_moments_repository import SQLiteMomentsRepository
    from ..sqlite.sqlite_analysis_report_repository import SQLiteAnalysisReportRepository
    from ..sqlite.sqlite_agent_repository import SQLiteAgentRepository
    from ..sqlite.sqlite_trading_repository import SQLiteTradingRepository
    from ..sqlite.sqlite_payment_repository import SQLitePaymentRepository
    from ..sqlite.sqlite_kronos_repository import SQLiteKronosRepository
    from ..sqlite.sqlite_openbb_repository import SQLiteOpenBBRepository
    from ..sqlite.sqlite_quantml_repository import SQLiteQuantMLFactorRepository

    from ..postgres.postgres_timescale_bar_repository import PostgresTimescaleBarRepository

    RepositoryRegistry.register(RepositoryType.MYSQL, "investment_manager", MySQLInvestmentManagerRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "basic_market_data", MySQLBasicMarketDataRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "news_archive", MySQLNewsArchiveRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "signal_flag_pool", MySQLSignalFlagPoolRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "moments", MySQLMomentsRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "analysis_report", MySQLAnalysisReportRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "agent", MySQLAgentRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "trading", MySQLTradingRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "payment", MySQLPaymentRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "kronos", MySQLKronosRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "openbb", MySQLOpenBBRepository)
    RepositoryRegistry.register(RepositoryType.MYSQL, "quantml", MySQLQuantMLFactorRepository)

    RepositoryRegistry.register(RepositoryType.SQLITE, "investment_manager", SQLiteInvestmentManagerRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "basic_market_data", SQLiteBasicMarketDataRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "news_archive", SQLiteNewsArchiveRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "signal_flag_pool", SQLiteSignalFlagPoolRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "moments", SQLiteMomentsRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "analysis_report", SQLiteAnalysisReportRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "agent", SQLiteAgentRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "trading", SQLiteTradingRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "payment", SQLitePaymentRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "kronos", SQLiteKronosRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "openbb", SQLiteOpenBBRepository)
    RepositoryRegistry.register(RepositoryType.SQLITE, "quantml", SQLiteQuantMLFactorRepository)

    RepositoryRegistry.register(RepositoryType.POSTGRES, "market_bars", PostgresTimescaleBarRepository)

    _REGISTERED = True


def ensure_registered():
    """Ensure all repositories are registered (idempotent)."""
    _register_all()
