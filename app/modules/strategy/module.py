"""Strategy bounded context module declaration."""

from __future__ import annotations

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry
from app.modules.health import module_health_check


@register_module(name="strategy", description="Strategy management and analysis")
class StrategyContextModule:
    """Strategy context: optimization, snapshots, recommendations, factors."""

    services = []
    routes = [
        "strategy_optimization",
        "strategy_snapshot",
        "strategy_shadow",
        "strategy_copilot",
        "recommendation",
        "review",
        "factor",
        "attribution",
    ]
    config_keys = []
    depends_on = ["market_data"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        StrategyContextModule.wire(container)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("strategy", ['mysql', 'redis'])
__all__ = ["StrategyContextModule"]
