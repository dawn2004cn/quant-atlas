"""Collaboration context module declaration."""

from __future__ import annotations

from app.core.registry import register_module
from app.modules.health import module_health_check


@register_module(name="collaboration", description="Team research and collaboration")
class CollaborationContextModule:
    """Collaboration context: tenants, teams, blackboard, workflow.

    Services live under ``app/modules/collaboration/services/``.
    Wired via ``wire_collaboration_module`` in bootstrap.
    """

    services = []  # wired procedurally until @register_service migration
    routes = [
        "collaboration",  # legacy name; routes.py provides the callable entry
    ]
    config_keys = ["ENABLE_COLLABORATION"]
    depends_on = ["system"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        from app.modules.collaboration import wire_module

        wire_module(services, session_factory)

    @staticmethod
    def initialize(container, session_factory=None) -> None:
        """Auto-invoked by ``initialize_all_modules`` when this module is enabled."""
        CollaborationContextModule.wire(container, session_factory)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("collaboration", ['redis', 'mysql'])
__all__ = ["CollaborationContextModule"]
