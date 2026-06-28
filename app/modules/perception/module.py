"""Perception bounded context module declaration."""

from __future__ import annotations

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry
from app.modules.health import module_health_check

@register_module(name="perception", description="10.0 perception and resonance")
class PerceptionContextModule:
    """Perception context: 10.0 manifest and resonance."""

    services = []
    routes = ["manifest_10", "resonance"]
    config_keys = ["PERCEPTION_ENABLED"]
    depends_on = ["mesh"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        PerceptionContextModule.wire(container)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("perception", ['redis'])
__all__ = ["PerceptionContextModule"]
