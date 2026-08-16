"""Data service wiring — data lake, Qlib, migration, moments, Kronos."""

from __future__ import annotations

import logging
from typing import Any

from app.core.registry import register_factory

logger = logging.getLogger(__name__)


def _make_data_lake_manager(reg: Any) -> Any:
    from app.modules.data.services.data_lake_manager import DataLakeManager
    return DataLakeManager(registry=reg)


register_factory("data_lake_manager", _make_data_lake_manager)


def _make_qlib_pipeline_service(reg: Any) -> Any:
    from pathlib import Path

    from app.config import get_settings
    from app.modules.data.services.qlib_pipeline_service import QlibPipelineService

    class _StubDataAccess:
        def fetch_daily_bars(self, symbols, market, start_date, end_date):
            return []

    data_access = _StubDataAccess()
    settings = get_settings()
    base_dir = Path(settings.qlib_export_path) if hasattr(settings, 'qlib_export_path') else Path("instance/qlib_export")
    return QlibPipelineService(
        data_access=data_access,
        base_dir=base_dir,
        tdx_root_path=getattr(settings, "tdx_root_path", None),
    )


register_factory("qlib_pipeline_service", _make_qlib_pipeline_service)


def _make_legacy_migration_service(reg: Any) -> Any:
    from app.modules.data.services.legacy_migration_service import LegacyDataMigrationService
    return LegacyDataMigrationService(registry=reg)


register_factory("legacy_migration_service", _make_legacy_migration_service)


def _make_data_migration_runner(reg: Any) -> Any:
    from app.modules.data.services.data_migration_runner import DataMigrationRunner
    return DataMigrationRunner(registry=reg)


register_factory("data_migration_runner", _make_data_migration_runner)






def _make_basic_market_data_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.infrastructure.repositories.common.deps import create_basic_market_data_repository
    from app.modules.data.services.basic_market_data_service import BasicMarketDataService
    settings = get_settings()
    repo = create_basic_market_data_repository(settings)
    return BasicMarketDataService(repository=repo)


register_factory("basic_market_data_service", _make_basic_market_data_service)


def _make_basic_knowledge_service(reg: Any) -> Any:
    from app.modules.data.services.basic_knowledge_service import BasicKnowledgeService

    news = reg.get_or_none("news_archive_repository") or reg.get_or_none("news_archive")
    if news is None:
        try:
            from app.config import get_settings
            from app.infrastructure.repositories.common.deps import create_news_archive_repository

            news = create_news_archive_repository(get_settings())
        except Exception:  # noqa: BLE001
            news = None

    fund = reg.get_or_none("tool_facade_service")
    if fund is None:
        fund = reg.get_or_none("fundamental_access")
    if fund is None:
        try:
            from app.modules.system.services.helpers.cn_fundamentals_access import (
                get_cn_fundamentals_port,
            )

            fund = get_cn_fundamentals_port()
        except Exception:  # noqa: BLE001
            fund = None

    return BasicKnowledgeService(
        basic_market_data_service=reg.get_or_none("basic_market_data_service"),
        news_archive=news,
        industry_chain_service=reg.get_or_none("industry_chain_service"),
        fundamental_access=fund,
    )


register_factory("basic_knowledge_service", _make_basic_knowledge_service)


def _make_tdx_block_stats_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.modules.data.services.tdx_block_stats_service import TdxBlockStatsService
    settings = get_settings()
    return TdxBlockStatsService(settings=settings)


register_factory("tdx_block_stats_service", _make_tdx_block_stats_service)
