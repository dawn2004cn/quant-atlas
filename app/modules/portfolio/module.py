"""Portfolio bounded context module declaration."""

from __future__ import annotations

from app.core.registry import register_module
from app.modules.health import module_health_check


@register_module(name="portfolio", description="Watchlist and portfolio UX")
class PortfolioContextModule:
    """Watchlist-focused context (holdings UX, agents, signal flags)."""

    services = []
    routes = ["watchlist_agent", "watchlist_experience", "signal_flag"]
    config_keys = []
    depends_on = ["system"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        pass

    @staticmethod
    def initialize(container) -> None:
        PortfolioContextModule.wire(container)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("portfolio", ['mysql', 'redis'])
__all__ = ["PortfolioContextModule"]
