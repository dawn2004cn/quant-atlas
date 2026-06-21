from __future__ import annotations
"""JSON graph descriptors for visual swarm orchestration (Quant Atlas 7.0)."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TopologyNodeKind(str, Enum):
    """Swarm Designer block types."""

    AGENT = "agent"
    FILTER = "filter"
    DEBATE = "debate"
    ARBITER = "arbiter"
    PARALLEL_GROUP = "parallel_group"
    SYNTHESIS = "synthesis"
    SUPERVISOR = "supervisor"
    VISION = "vision"


class TopologyNode(BaseModel):
    """One node in a swarm research pipeline."""

    id: str
    kind: TopologyNodeKind
    agent_role: str = ""
    label: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class TopologyEdge(BaseModel):
    """Directed information flow between nodes."""

    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")
    condition: str | None = None

    model_config = {"populate_by_name": True}


class SwarmTopologyDescriptor(BaseModel):
    """User- or preset-defined LangGraph topology."""

    schema_version: str = "v1"
    id: str
    name: str
    description: str = ""
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)
    entry_node: str = ""
    exit_node: str = ""

    @model_validator(mode="after")
    def _validate_graph(self) -> SwarmTopologyDescriptor:
        node_ids = {n.id for n in self.nodes}
        if self.entry_node and self.entry_node not in node_ids:
            raise ValueError(f"entry_node '{self.entry_node}' not in nodes")
        if self.exit_node and self.exit_node not in node_ids:
            raise ValueError(f"exit_node '{self.exit_node}' not in nodes")
        for edge in self.edges:
            if edge.from_id not in node_ids:
                raise ValueError(f"edge.from '{edge.from_id}' not in nodes")
            if edge.to_id not in node_ids:
                raise ValueError(f"edge.to '{edge.to_id}' not in nodes")
        return self

    def node_map(self) -> dict[str, TopologyNode]:
        return {n.id: n for n in self.nodes}

    def outgoing(self, node_id: str) -> list[TopologyEdge]:
        return [e for e in self.edges if e.from_id == node_id]

    def linear_execution_order(self) -> list[str]:
        """Return a topological walk from entry_node (supports simple DAGs)."""
        if not self.entry_node:
            return [n.id for n in self.nodes]
        order: list[str] = []
        visited: set[str] = set()
        stack = [self.entry_node]
        while stack:
            cur = stack.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            order.append(cur)
            for edge in self.outgoing(cur):
                if edge.to_id not in visited:
                    stack.append(edge.to_id)
        return order
