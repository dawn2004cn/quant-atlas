"""User bounded context module declaration."""

from __future__ import annotations

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry
from app.modules.health import module_health_check

@register_module(name="user", description="User management")
class UserContextModule:
    """User context: profiles, lifecycle, moments."""

    services = []
    routes = ["user_profile", "user_lifecycle", "moments", "retail_assistant"]
    config_keys = []
    depends_on = ["system"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        UserContextModule.wire(container)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("user", ['mysql', 'redis'])
__all__ = ["UserContextModule"]
