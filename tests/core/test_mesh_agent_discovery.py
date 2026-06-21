from __future__ import annotations

from app.core.mesh.agent_discovery import AgentDiscoveryProtocol, research_topology_capabilities
from app.core.mesh.node_registry import MeshNodeRegistry, default_local_node


def test_research_topology_capabilities_non_empty() -> None:
    caps = research_topology_capabilities()
    assert "macro_analyst" in caps or "supervisor" in caps


def test_agent_discovery_lists_local_agents() -> None:
    protocol = AgentDiscoveryProtocol(registry=MeshNodeRegistry())
    out = protocol.discover(role="macro")
    assert out["ok"] is True
    assert out["count"] >= 0


def test_agent_discovery_merges_mesh_node() -> None:
    registry = MeshNodeRegistry()
    registry.register(
        default_local_node(node_id="us-node-1", region="US", roles=["technical_agent"])
    )
    protocol = AgentDiscoveryProtocol(registry=registry)
    out = protocol.discover(region="US")
    assert out["count"] >= 1
