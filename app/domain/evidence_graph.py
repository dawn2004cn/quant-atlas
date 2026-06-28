from __future__ import annotations

"""Evidence Graph — directed provenance graph for decision traceability.

Node types
----------
- ``data_source`` — raw input (bars, quote, financials)
- ``capability`` — a tool capability execution (fetch_bars, news_bundle, …)
- ``reasoning`` — AI reasoning step or analysis
- ``decision`` — final conclusion (signal, recommendation, trade)

Edge labels
-----------
- ``feeds_into`` — data → capability → reasoning → decision
- ``contradicts`` — conflicting evidence
- ``supports`` — supporting evidence
"""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    DATA_SOURCE = "data_source"
    CAPABILITY = "capability"
    REASONING = "reasoning"
    DECISION = "decision"
    WORKFLOW = "workflow"


class EdgeLabel(str, Enum):
    FEEDS_INTO = "feeds_into"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVES_FROM = "derives_from"


@dataclass(frozen=True)
class EvidenceNode:
    """A single node in the evidence graph."""

    id: str
    node_type: NodeType
    label: str
    summary: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "label": self.label,
            "summary": self.summary,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class EvidenceEdge:
    """A directed edge between two evidence nodes."""

    source_id: str
    target_id: str
    label: EdgeLabel = EdgeLabel.FEEDS_INTO
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "label": self.label.value,
            "metadata": self.metadata,
        }


@dataclass
class EvidenceGraph:
    """A provenance graph that tracks how a decision was reached.

    Serialises to a JSON structure suitable for frontend DAG rendering.
    """

    graph_id: str
    subject: str
    nodes: dict[str, EvidenceNode] = field(default_factory=dict)
    edges: list[EvidenceEdge] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_node(self, node: EvidenceNode) -> str:
        self.nodes[node.id] = node
        return node.id

    def add_edge(self, edge: EvidenceEdge) -> None:
        self.edges.append(edge)

    def link(
        self,
        source_id: str,
        target_id: str,
        label: EdgeLabel = EdgeLabel.FEEDS_INTO,
        **metadata: Any,
    ) -> None:
        self.edges.append(EvidenceEdge(source_id=source_id, target_id=target_id, label=label, metadata=metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "subject": self.subject,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "created_at": self.created_at.isoformat(),
        }

    def merge(self, other: EvidenceGraph) -> None:
        """Merge another graph's nodes and edges into this one."""
        for nid, node in other.nodes.items():
            if nid not in self.nodes:
                self.nodes[nid] = node
        self.edges.extend(other.edges)
