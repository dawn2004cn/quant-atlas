from app.application.services._shim_policy import warn_shim_import

warn_shim_import("app.application.services.watchlist_service")

from app.modules.market_data.services.watchlist_service import WatchlistApplicationService  # noqa: F401

__all__ = ["WatchlistApplicationService"]
