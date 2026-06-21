from __future__ import annotations

from app.agents.research.topology_loader import TopologyLoader
from app.agents.research.state import RESEARCH_GRAPH_NODES


def test_topology_loader_loads_default_graph() -> None:
    topo = TopologyLoader.load_default()
    assert topo.id == "research_default"
    assert topo.entry_node == "supervisor"
    assert topo.exit_node == "decision_dashboard"
    assert len(topo.nodes) >= 12
    assert len(topo.conditional_edges) == 5


def test_research_graph_nodes_match_topology() -> None:
    topo_ids = set(TopologyLoader.load_default().all_node_ids())
    for node_id in RESEARCH_GRAPH_NODES:
        assert node_id in topo_ids
