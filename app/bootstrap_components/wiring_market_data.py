"""Market data service wiring — stock, watchlist, signal, sector."""

from __future__ import annotations

import logging
from typing import Any

from app.core.registry import register_factory

logger = logging.getLogger(__name__)


def _make_stock_service(reg: Any) -> Any:
    from app.modules.market_data.services.stock_service import StockApplicationService
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider
    mp = get_market_data_provider()
    return StockApplicationService(
        market_provider=mp,
        indicator_provider=None,
        news_provider=None,
        global_market_service=None,
        stock_cache=None,
    )


register_factory("stock_service", _make_stock_service)


def _make_market_service(reg: Any) -> Any:
    from app.modules.market_data.services.market_service import MarketApplicationService
    return MarketApplicationService()


register_factory("market_service", _make_market_service)


def _make_market_facade(reg):
    from app.modules.market_data.services.market_service import MarketApplicationService
    return MarketApplicationService()

register_factory("market_facade", _make_market_facade)


def _make_watchlist_service(reg: Any) -> Any:
    from app.bootstrap_components.service_wiring import resolve_registry_session_factory
    from app.config import CONFIG_DIR, get_settings
    from app.infrastructure.repositories.deps import create_stock_group_repository, create_watchlist_repository
    from app.modules.market_data.services.watchlist_service import WatchlistApplicationService
    from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

    settings = get_settings()
    sf = resolve_registry_session_factory(reg)
    if settings.use_mysql and sf is not None:
        watchlist_repo = create_watchlist_repository(settings, session_factory=sf)
        stock_group_repo = create_stock_group_repository(settings, session_factory=sf)
    else:
        from app.infrastructure.repositories.common.json_repositories import (
            JsonStockGroupRepository,
            JsonWatchlistRepository,
        )
        watchlist_repo = JsonWatchlistRepository(CONFIG_DIR / "watchlist.json")
        stock_group_repo = JsonStockGroupRepository(
            CONFIG_DIR / "stock_groups.json",
            watchlist_repository=watchlist_repo,
        )
        logger.info("watchlist_service using JSON repositories (use_mysql=%s)", settings.use_mysql)

    return WatchlistApplicationService(
        repository=watchlist_repo,
        stock_group_repository=stock_group_repo,
        market_provider=get_market_data_provider(),
    )


register_factory("watchlist_service", _make_watchlist_service)


def _make_stock_group_service(reg: Any) -> Any:
    from app.bootstrap_components.service_wiring import resolve_registry_session_factory
    from app.config import CONFIG_DIR, get_settings
    from app.infrastructure.repositories.deps import create_stock_group_repository
    from app.modules.market_data.services.stock_group_service import StockGroupApplicationService

    settings = get_settings()
    sf = resolve_registry_session_factory(reg)
    if settings.use_mysql and sf is not None:
        repo = create_stock_group_repository(settings, session_factory=sf)
    else:
        from app.infrastructure.repositories.common.json_repositories import (
            JsonStockGroupRepository,
            JsonWatchlistRepository,
        )
        watchlist_repo = JsonWatchlistRepository(CONFIG_DIR / "watchlist.json")
        repo = JsonStockGroupRepository(
            CONFIG_DIR / "stock_groups.json",
            watchlist_repository=watchlist_repo,
        )
        logger.info("stock_group_service using JSON repositories (use_mysql=%s)", settings.use_mysql)

    return StockGroupApplicationService(repository=repo)


register_factory("stock_group_service", _make_stock_group_service)


def _make_signal_flag_service(reg: Any) -> Any:
    from app.bootstrap_components.service_wiring import resolve_registry_session_factory
    from app.config import get_settings
    from app.infrastructure.repositories.deps import create_signal_flag_pool_repository, create_stock_cache
    from app.modules.strategy.services.strategy.signal_flag_service import SignalFlagScannerService
    settings = get_settings()
    sf = resolve_registry_session_factory(reg)
    stock_svc = reg.get_or_none("stock_service")
    return SignalFlagScannerService(
        stock_service=stock_svc,
        stock_cache=create_stock_cache(),
        repository=create_signal_flag_pool_repository(settings, session_factory=sf),
        enable_qlib=bool(getattr(settings, "enable_qlib", False)),
    )


register_factory("signal_flag_service", _make_signal_flag_service)


def _make_hot_sector_storage_service(reg: Any) -> Any:
    from app.config import get_settings
    from app.modules.market_data.services.hot_sector_storage_service import HotSectorStorageService
    settings = get_settings()
    return HotSectorStorageService(settings=settings)


register_factory("hot_sector_storage_service", _make_hot_sector_storage_service)





def _make_watchlist_agent_service(reg: Any) -> Any:
    from app.modules.market_data.services.watchlist_agent_service import WatchlistAgentService
    return WatchlistAgentService(
        market_service=reg.get("market_service"),
        stock_service=reg.get("stock_service"),
        watchlist_service=reg.get("watchlist_service"),
        stock_group_service=reg.get("stock_group_service"),
    )


register_factory("watchlist_agent_service", _make_watchlist_agent_service)


def _make_watchlist_experience_service(reg: Any) -> Any:
    from app.modules.market_data.services.watchlist_experience_service import WatchlistExperienceService
    return WatchlistExperienceService(
        watchlist_agent_service=reg.get("watchlist_agent_service"),
        review_tracking_service=reg.get_or_none("review_tracking_service"),
    )


register_factory("watchlist_experience_service", _make_watchlist_experience_service)
