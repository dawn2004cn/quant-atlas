from app.application.services._shim_policy import warn_shim_import

warn_shim_import("app.application.services.strategy_service")

from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService  # noqa: F401

__all__ = ["StrategyApplicationService"]
