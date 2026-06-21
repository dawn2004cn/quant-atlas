"""Market data bounded context module declaration."""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
from typing import Any

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry

@register_module(name="market_data", description="Market data access and analysis")
class MarketDataContextModule:
    """Market data context: stocks, quotes, history, sectors.

    This context provides access to all market data:
    - Stock details, quotes, and historical data
    - Market core and auxiliary data
    - Global market data
    - Hot sectors and industry chains
    - TDX blocks and sentiment data
    """

    services = []
    routes = [
        "stock",
        "market_core",
        "market_aux",
        "global_market",
        "hot_sectors",
        "tdx_base",
        "sentiment",
        "industry_chain",
    ]
    config_keys = []
    depends_on = ["system"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        """Wire market data services.

        Migrated from ``services.py`` ``_try_init_*`` methods (Phase 4.1).
        """
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        """Auto-invoked by ``initialize_all_modules``."""
        MarketDataContextModule.wire(container)


def _init_market_service(services: Any) -> None:
    """Initialize MarketApplicationService (migrated from services.py)."""
    if getattr(services, "market_service", None) is not None:
        return
    try:
        from app.infrastructure.providers.cn_industry_provider import CnIndustryProvider
        from app.modules.system.services.helpers.market_data_provider import get_market_data_provider
        from app.modules.market_data.services.cn_quote_snapshot import configure_cn_quote_snapshot
        from app.modules.market_data.services.market_service import MarketApplicationService

        market_provider = get_market_data_provider()
        industry_provider = CnIndustryProvider()
        stock_cache = getattr(services, "_stock_cache", None)
        services.market_service = MarketApplicationService(
            market_provider, industry_provider, stock_cache=stock_cache
        )
        configure_cn_quote_snapshot(
            market_service=services.market_service,
            market_provider=market_provider,
        )
    except Exception as e:
        logger.warning("market_data.module._init_market_service: %s", e)


def _init_market_narrative_service(services: Any) -> None:
    """Initialize MarketNarrativeService (migrated from services.py)."""
    if getattr(services, "market_narrative_service", None) is not None:
        return
    if getattr(services, "market_service", None) is None:
        return
    try:
        from app.modules.market_data.services.market_narrative_service import MarketNarrativeService

        services.market_narrative_service = MarketNarrativeService(
            market_service=services.market_service,
            ai_adapter=None,
        )
    except Exception as e:
        logger.warning("market_data.module._init_market_narrative_service: %s", e)


def _init_global_market_service(services: Any) -> None:
    """Initialize GlobalMarketService (migrated from services.py)."""
    if getattr(services, "global_market_service", None) is not None:
        return
    try:
        from app.modules.system.services.helpers.market_data_provider import get_market_data_provider
        from app.modules.market_data.services.global_market_service import GlobalMarketService

        market_provider = get_market_data_provider()
        repository = None
        try:
            from app.config import get_settings
            from app.infrastructure.repositories.sqlite.sqlite_openbb_repository import SQLiteOpenBBRepository

            settings = get_settings()
            db_path = getattr(settings, "data_dir", ".") if settings else "."
            repository = SQLiteOpenBBRepository(db_path=f"{db_path}/openbb_cache.db")
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass

        if repository is None:
            class InMemoryOpenBBRepository:
                """Simple in-memory fallback for OpenBBRepository."""
                def __init__(self):
                    self._cache = {}
                def get_cached_data(self, provider, symbol, data_type, timeframe=None):
                    key = f"{provider}:{symbol}:{data_type}:{timeframe or 'default'}"
                    return self._cache.get(key)
                def cache_data(self, provider, symbol, data_type, payload, timeframe=None, ttl_hours=24):
                    key = f"{provider}:{symbol}:{data_type}:{timeframe or 'default'}"
                    self._cache[key] = payload
                def get_provider_config(self, provider_name):
                    return None
                def save_provider_config(self, config):
                    pass
                def save_data(self, key, data):
                    self._cache[key] = data
                    return True
                def get_data(self, key):
                    return self._cache.get(key)

            repository = InMemoryOpenBBRepository()

        services.global_market_service = GlobalMarketService(market_provider, repository)
    except Exception as e:
        logger.warning("market_data.module._init_global_market_service: %s", e)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("market_data", ['mysql', 'openbb'])
__all__ = ["MarketDataContextModule"]
