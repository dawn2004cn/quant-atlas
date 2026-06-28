from __future__ import annotations
"""Research LangGraph topology descriptor (data-driven, 7.0)."""


from pydantic import BaseModel, Field

from app.domain.topology_schema import SwarmTopologyDescriptor, TopologyEdge


class DebateConfig(BaseModel):
    investment_rounds: int = 3
    risk_rounds: int = 3


class ConditionalEdge(BaseModel):
    from_id: str = Field(alias="from")
    router: str
    mapping: dict[str, str] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class ResearchGraphTopology(SwarmTopologyDescriptor):
    """Full research graph including conditional routers."""

    debate: DebateConfig = Field(default_factory=DebateConfig)
    conditional_edges: list[ConditionalEdge] = Field(default_factory=list)

    def static_edges(self) -> list[TopologyEdge]:
        return list(self.edges)

    def conditional_routers(self) -> list[ConditionalEdge]:
        return list(self.conditional_edges)

    def all_node_ids(self) -> tuple[str, ...]:
        return tuple(n.id for n in self.nodes)

    def validate_registry(self, registered: set[str]) -> list[str]:
        """Return node ids present in JSON but missing from runtime registry."""
        missing = [nid for nid in self.all_node_ids() if nid not in registered]
        extra = sorted(registered - set(self.all_node_ids()))
        if extra:
            missing.extend([f"+extra:{nid}" for nid in extra])
        return missing


__all__ = [
    "DebateConfig",
    "ConditionalEdge",
    "ResearchGraphTopology",
]
