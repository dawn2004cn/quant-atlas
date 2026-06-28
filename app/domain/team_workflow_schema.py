from __future__ import annotations

"""Human + Agent hybrid team workflow descriptors (Quant Atlas 8.0 P1)."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class WorkflowNodeKind(str, Enum):
    """Team pipeline block types — human gates + agent swarms."""

    START = "start"
    END = "end"
    HUMAN_TASK = "human_task"
    APPROVAL_GATE = "approval_gate"
    BLACKBOARD_POST = "blackboard_post"
    RESEARCH_PUBLISH = "research_publish"
    AGENT_SWARM = "agent_swarm"
    ARBITER = "arbiter"


class TeamWorkflowNode(BaseModel):
    id: str
    kind: WorkflowNodeKind
    label: str = ""
    assignee_role: str = "member"
    agent_topology_id: str = ""
    agent_role: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class TeamWorkflowEdge(BaseModel):
    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")
    condition: str | None = None

    model_config = {"populate_by_name": True}


class TeamWorkflowDescriptor(BaseModel):
    """Lead-defined multi-human + multi-agent research pipeline."""

    schema_version: str = "v1"
    id: str
    name: str
    description: str = ""
    team_id: int | None = None
    nodes: list[TeamWorkflowNode] = Field(default_factory=list)
    edges: list[TeamWorkflowEdge] = Field(default_factory=list)
    entry_node: str = ""
    exit_node: str = ""

    @model_validator(mode="after")
    def _validate_graph(self) -> TeamWorkflowDescriptor:
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

    def node_map(self) -> dict[str, TeamWorkflowNode]:
        return {n.id: n for n in self.nodes}

    def next_node_id(self, current_id: str) -> str | None:
        for edge in self.edges:
            if edge.from_id == current_id:
                return edge.to_id
        return None


__all__ = [
    "WorkflowNodeKind",
    "TeamWorkflowNode",
    "TeamWorkflowEdge",
    "TeamWorkflowDescriptor",
]
