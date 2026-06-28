"""Delegate watchlist service initialization to keep services.py lightweight."""
import logging

from app.modules.market_data.services.stock_group_service import StockGroupApplicationService
from app.modules.market_data.services.watchlist_service import WatchlistApplicationService

logger = logging.getLogger(__name__)

def init_watchlist_services(services, repositories):
    """Initialize watchlist, stock_group, watchlist_agent, and watchlist_experience services."""
    if not repositories:
        return
    watchlist_repo = getattr(repositories, "watchlist_repository", None)
    stock_group_repo = getattr(repositories, "stock_group_repository", None)

    if watchlist_repo:
        services.watchlist_service = WatchlistApplicationService(
            repository=watchlist_repo,
            stock_group_repository=stock_group_repo,
        )

    if stock_group_repo:
        services.stock_group_service = StockGroupApplicationService(
            repository=stock_group_repo,
        )

    if all([
        services.watchlist_service,
        services.stock_group_service,
        services.market_service,
        services.stock_service,
    ]):
        from app.modules.market_data.services.watchlist_agent_service import WatchlistAgentService
        services.watchlist_agent_service = WatchlistAgentService(
            market_service=services.market_service,
            stock_service=services.stock_service,
            watchlist_service=services.watchlist_service,
            stock_group_service=services.stock_group_service,
        )

        from app.modules.market_data.services.watchlist_experience_service import WatchlistExperienceService
        services.watchlist_experience_service = WatchlistExperienceService(
            watchlist_agent_service=services.watchlist_agent_service,
        )

def init_stock_group_service(services, repositories):
    """Initialize stock_group_service as a standalone backup init."""
    if not repositories:
        return
    stock_group_repo = getattr(repositories, "stock_group_repository", None)
    if stock_group_repo:
        services.stock_group_service = StockGroupApplicationService(
            repository=stock_group_repo,
        )
