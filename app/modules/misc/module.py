"""Miscellaneous bounded context module declaration."""

from __future__ import annotations

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry
from app.modules.health import module_health_check


@register_module(name="misc", description="Miscellaneous features")
class MiscContextModule:
    """Miscellaneous context: admin, investment managers, integration."""

    services = []
    routes = [
        "admin_stock_cache",
        "investment_manager",
        "integration_stack",
        "daily_workbench",
        "diagnosis",
        "nl",
        "challenge",
        "ten_kings",
        "ui",
        "portfolio_user",
        "signal_flag",
    ]
    config_keys = []
    depends_on = ["system"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        MiscContextModule.wire(container)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("misc", [])
__all__ = ["MiscContextModule"]
