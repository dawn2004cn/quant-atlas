"""Visual Logic Canvas — Phase 13. Drag-drop factor composition engine with Qlib code generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CanvasNode:
    """A single node in the visual logic canvas."""
    node_id: str
    node_type: Literal["data_source", "factor", "operator", "condition", "output"]
    label: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    inputs: list[str] = field(default_factory=list)
    position: dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})


@dataclass
class CanvasGraph:
    """A complete canvas graph representing a strategy."""
    graph_id: str
    name: str
    nodes: list[CanvasNode] = field(default_factory=list)
    edges: list[dict[str, str]] = field(default_factory=list)  # [{from, to}]
    created_at: str = ""
    user_id: int = 0


class CanvasService:
    """Visual Logic Canvas — drag-drop factor composition → Qlib code generation."""

    def __init__(self):
        self._graphs: dict[str, CanvasGraph] = {}

    def create_graph(self, user_id: int, name: str) -> CanvasGraph:
        """Create a new canvas graph."""
        graph = CanvasGraph(
            graph_id=str(uuid4().hex[:12]),
            name=name,
            user_id=user_id,
        )
        self._graphs[graph.graph_id] = graph
        return graph

    def add_node(self, graph_id: str, node: CanvasNode) -> CanvasGraph:
        """Add a node to the canvas."""
        graph = self._graphs.get(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
        graph.nodes.append(node)
        return graph

    def add_edge(self, graph_id: str, from_node: str, to_node: str) -> CanvasGraph:
        """Connect two nodes."""
        graph = self._graphs.get(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
        graph.edges.append({"from": from_node, "to": to_node})
        return graph

    def generate_qlib_code(self, graph_id: str) -> str:
        """Generate Qlib-compatible strategy code from canvas graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return "# Graph not found"

        lines = [
            "# Auto-generated strategy from Visual Canvas",
            '# Graph: ' + graph.name,
            '',
            'from qlib.contrib.strategy import TopkDropoutStrategy',
            '',
            '# === Data Sources ===',
        ]

        for node in graph.nodes:
            if node.node_type == "data_source":
                lines.append(f"# Source: {node.label} ({node.params.get('symbol', 'unknown')})")
            elif node.node_type == "factor":
                lines.append(f"# Factor: {node.label} params={json.dumps(node.params)}")
            elif node.node_type == "operator":
                lines.append(f"# Operator: {node.label}")
            elif node.node_type == "condition":
                lines.append(f"# Condition: {node.label} → {node.params.get('threshold', 'N/A')}")

        lines.extend([
            '',
            "strategy = TopkDropoutStrategy(",
            "    topk=10,",
            "    dropout=5,",
            ")",
            '',
        ])
        return '\n'.join(lines)

    def to_json(self, graph_id: str) -> dict:
        """Export graph as JSON for frontend rendering."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return {}
        return {
            "graph_id": graph.graph_id,
            "name": graph.name,
            "nodes": [n.__dict__ for n in graph.nodes],
            "edges": graph.edges,
        }
