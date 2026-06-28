"""Research bounded context module declaration."""

from __future__ import annotations

from app.core.module_registry import register_module
from app.core.typed_registry import get_registry
from app.modules.health import module_health_check

@register_module(name="research", description="Research workflows and simulation")
class ResearchContextModule:
    """Research context: agent swarm, simulation, decision replay."""

    services = []
    routes = [
        "agent_swarm",
        "swarm_topology",
        "simulation",
        "decision_replay",
        "decision_theater",
        "workflow",
        "evidence_graph",
    ]
    config_keys = []
    depends_on = ["ai_agent"]

    @staticmethod
    def wire(services, session_factory=None) -> None:
        reg = get_registry()
        reg.wire_to(services)

    @staticmethod
    def initialize(container) -> None:
        ResearchContextModule.wire(container)



    @staticmethod
    def check_health() -> dict:
        return module_health_check("research", ['mysql'])
__all__ = ["ResearchContextModule"]
