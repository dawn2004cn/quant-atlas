"""Research Service Adapters.

Adapters implement the Research Ports using the current concrete services.
Each adapter wraps an existing service and adapts its interface to match
the corresponding port contract.

This enables:
1. Clean separation between route handlers and service implementations
2. Easy substitution of service implementations in tests
3. Clear migration path to independent microservice
"""

from __future__ import annotations

from typing import Any

from app.modules.research.ports import (
    AgentSwarmPort,
    DecisionReplayPort,
    DecisionTheaterPort,
    EvidenceGraphPort,
    SimulationPort,
    SwarmTopologyPort,
    WorkflowPort,
)


class AgentSwarmAdapter(AgentSwarmPort):
    """Adapts agent swarm service to AgentSwarmPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_status(self, task_id: str) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_status(task_id)
        return {"status": "unknown", "agents": []}


class DecisionReplayAdapter(DecisionReplayPort):
    """Adapts decision replay service to DecisionReplayPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_replay(self, decision_id: str) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_replay(decision_id)
        return {"replay": {}}


class DecisionTheaterAdapter(DecisionTheaterPort):
    """Adapts decision theater service to DecisionTheaterPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_theater(self, decision_id: str) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_theater(decision_id)
        return {"theater": {}}


class EvidenceGraphAdapter(EvidenceGraphPort):
    """Adapts evidence graph service to EvidenceGraphPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def query(self, query: str) -> dict[str, Any]:
        if self._service is not None:
            return self._service.query(query)
        return {"graph": {}}


class SimulationAdapter(SimulationPort):
    """Adapts simulation service to SimulationPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._service is not None:
            return self._service.run(params)
        return {"result": {}}


class SwarmTopologyAdapter(SwarmTopologyPort):
    """Adapts swarm topology service to SwarmTopologyPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_topology(self) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_topology()
        return {"topology": {}}


class WorkflowAdapter(WorkflowPort):
    """Adapts workflow service to WorkflowPort."""

    def __init__(self, service: Any = None) -> None:
        self._service = service

    def get_status(self, workflow_id: str) -> dict[str, Any]:
        if self._service is not None:
            return self._service.get_status(workflow_id)
        return {"status": {}}


def create_research_ports(ctx: Any) -> dict[str, Any]:
    """Create all research ports from an ApiV1Context.

    This factory function maps context services to port adapters.
    Returns a dict of port_name -> port_instance.
    """
    ports = {}

    if getattr(ctx, "swarm_agent_service", None) is not None:
        ports["agent_swarm"] = AgentSwarmAdapter(ctx.swarm_agent_service)

    if getattr(ctx, "decision_replay_space_service", None) is not None:
        ports["decision_replay"] = DecisionReplayAdapter(
            ctx.decision_replay_space_service
        )

    if getattr(ctx, "decision_theater_service", None) is not None:
        ports["decision_theater"] = DecisionTheaterAdapter(ctx.decision_theater_service)

    if getattr(ctx, "evidence_graph_service", None) is not None:
        ports["evidence_graph"] = EvidenceGraphAdapter(ctx.evidence_graph_service)

    if getattr(ctx, "simulation_gateway_service", None) is not None:
        ports["simulation"] = SimulationAdapter(ctx.simulation_gateway_service)

    if getattr(ctx, "swarm_topology_service", None) is not None:
        ports["swarm_topology"] = SwarmTopologyAdapter(ctx.swarm_topology_service)

    if getattr(ctx, "workflow_service", None) is not None:
        ports["workflow"] = WorkflowAdapter(ctx.workflow_service)

    return ports


__all__ = [
    "AgentSwarmPort",
    "DecisionReplayPort",
    "DecisionTheaterPort",
    "EvidenceGraphPort",
    "SimulationPort",
    "SwarmTopologyPort",
    "WorkflowPort",
    "AgentSwarmAdapter",
    "DecisionReplayAdapter",
    "DecisionTheaterAdapter",
    "EvidenceGraphAdapter",
    "SimulationAdapter",
    "SwarmTopologyAdapter",
    "WorkflowAdapter",
    "create_research_ports",
]
