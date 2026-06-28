"""Execution bounded context module declaration."""

from __future__ import annotations

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry
from app.modules.health import module_health_check


@register_module(name="execution", description="Trade execution infrastructure")
class ExecutionContextModule:
    """Execution context: borderless execution, self-healing execution.

    Services live under ``app/modules/execution/services/``.
    Wired via ``wire_borderless_execution_service`` / ``wire_self_healing_execution_service``.
    """

    services = []
    routes = [
        "execution",
        "self_healing_execution",
    ]
    config_keys = []
    depends_on = ["portfolio"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        """Auto-invoked by ``initialize_all_modules`` when this module is enabled."""
        ExecutionContextModule.wire(container)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("execution", ['redis', 'mysql'])
__all__ = ["ExecutionContextModule"]
