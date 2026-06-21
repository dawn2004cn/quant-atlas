"""System bounded context module declaration."""

from __future__ import annotations

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry

@register_module(name="system", description="Core system infrastructure")
class SystemContextModule:
    """System context: health, monitoring, alerts, task management."""

    services = []
    routes = ["health", "system", "alert_center", "task_ops"]
    config_keys = []
    depends_on = []

    @staticmethod
    def wire(services, session_factory=None) -> None:
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        SystemContextModule.wire(container)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("system", [])
__all__ = ["SystemContextModule"]
