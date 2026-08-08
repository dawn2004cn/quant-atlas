"""Data bounded context module declaration."""

from __future__ import annotations

import logging
from typing import Any

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry

@register_module(name="data", description="Data infrastructure and pipelines")
class DataContextModule:
    """Data context: Qlib, task pipeline, data optimization."""

    services = []
    routes = [
        "qlib_rd",
        "task_pipeline",
        "data_infrastructure",
        "data_truth",
        "memory_optimization",
    ]
    config_keys = []
    depends_on = ["system"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        DataContextModule.wire(container)


def _init_basic_market_data_service(services: Any) -> None:
    """Initialize BasicMarketDataService (migrated from services.py)."""
    if getattr(services, "basic_market_data_service", None) is not None:
        return
    try:
        from app.config import get_settings
        from app.modules.data.services.data_lake_manager import DataLakeManager
        from app.infrastructure.repositories.data_lake_basic_market_data_repository import DataLakeBasicMarketDataRepository
        from app.modules.system.services.helpers.market_data_ingestor_access import create_longhu_ingestor
        from app.modules.data.services.basic_market_data_service import BasicMarketDataService

        s = get_settings()
        # Use DataLakeManager instead of old repository creation
        lake_manager: DataLakeManager = services.get("data_lake_manager")
        repo = DataLakeBasicMarketDataRepository(lake_manager=lake_manager)

        # Auto-ingest longhu data if none exists
        if repo.count_longhu_rows() == 0:
            try:
                svc = BasicMarketDataService(
                    repository=repo,
                    longhu_adapter=create_longhu_ingestor(),
                )
                svc.ingest_longhu_em(lookback_calendar_days=7)
                logger.info("Auto-ingested longhu data for initial setup")
            except Exception as e:
                logger.warning("data.module._init_basic_market_data_service auto-ingest: %s", e)

        longhu_adapter = create_longhu_ingestor()
        services.basic_market_data_service = BasicMarketDataService(
            repository=repo,
            longhu_adapter=longhu_adapter,
        )
    except Exception as e:
        logger.warning("data.module._init_basic_market_data_service: %s", e)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("data", ['mysql'])
__all__ = ["DataContextModule"]
