from __future__ import annotations

"""Cross-node agent discovery protocol for federated mesh (V9 / 分布式集群)."""

from typing import Any

from app.core.logger import get_logger
from app.core.mesh.node_registry import MeshNodeRegistry
from app.domain.mesh_schema import MeshNodeDescriptor

logger = get_logger(__name__)


def research_topology_capabilities() -> list[str]:
    """Agent roles advertised by this node from ``research_graph_topology.json``."""
    try:
        from app.agents.research.topology_loader import TopologyLoader

        topo = TopologyLoader.load_default()
        caps: list[str] = []
        for node in topo.nodes:
            role = (node.agent_role or node.id or "").strip()
            if role and role not in caps:
                caps.append(role)
        return caps
    except Exception as exc:
        logger.debug("research topology capabilities: %s", exc)
        return []


def build_local_mesh_capabilities() -> list[str]:
    """Capabilities merged into local ``MeshNodeDescriptor`` on bridge start."""
    base = ["event_fanout", "federated_agents", "research_graph"]
    for role in research_topology_capabilities():
        if role not in base:
            base.append(role)
    return base


class AgentDiscoveryProtocol:
    """Discover agent roles across mesh peers and local research topology."""

    def __init__(self, registry: MeshNodeRegistry | None = None) -> None:
        self._registry = registry

    def local_agents(self) -> list[dict[str, Any]]:
        try:
            from app.agents.research.topology_loader import TopologyLoader

            topo = TopologyLoader.load_default()
        except Exception as exc:
            logger.debug("local_agents topology: %s", exc)
            return []
        return [
            {
                "agent_id": node.id,
                "agent_role": node.agent_role or node.id,
                "kind": str(node.kind.value if hasattr(node.kind, "value") else node.kind),
                "label": node.label,
                "source": "local_topology",
                "topology_id": topo.id,
            }
            for node in topo.nodes
        ]

    def discover(
        self,
        *,
        role: str | None = None,
        region: str | None = None,
        include_local: bool = True,
    ) -> dict[str, Any]:
        role_key = (role or "").strip().lower()
        region_key = (region or "").strip().upper()
        agents: list[dict[str, Any]] = []

        if include_local:
            for row in self.local_agents():
                if role_key and role_key not in str(row.get("agent_role", "")).lower():
                    continue
                agents.append({**row, "node_id": "local", "region": region_key or "LOCAL"})

        if self._registry is not None:
            for node in self._registry.list_nodes():
                if region_key and str(node.region.value if hasattr(node.region, "value") else node.region) != region_key:
                    continue
                agents.extend(self._agents_from_node(node, role_key=role_key))

        return {
            "ok": True,
            "count": len(agents),
            "agents": agents,
            "filters": {"role": role or None, "region": region or None},
        }

    @staticmethod
    def _agents_from_node(node: MeshNodeDescriptor, *, role_key: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        region = str(node.region.value if hasattr(node.region, "value") else node.region)
        for mesh_role in node.roles:
            role_name = str(mesh_role.value if hasattr(mesh_role, "value") else mesh_role)
            if role_key and role_key not in role_name.lower():
                continue
            rows.append(
                {
                    "agent_id": f"{node.node_id}:{role_name}",
                    "agent_role": role_name,
                    "node_id": node.node_id,
                    "region": region,
                    "source": "mesh_registry",
                    "status": node.status,
                    "endpoint": node.endpoint,
                }
            )
        for cap in node.capabilities:
            cap_l = str(cap).lower()
            if role_key and role_key not in cap_l:
                continue
            if any(r.get("agent_role") == cap for r in rows):
                continue
            rows.append(
                {
                    "agent_id": f"{node.node_id}:{cap}",
                    "agent_role": cap,
                    "node_id": node.node_id,
                    "region": region,
                    "source": "mesh_capability",
                    "status": node.status,
                    "endpoint": node.endpoint,
                }
            )
        return rows


__all__ = [
    "AgentDiscoveryProtocol",
    "build_local_mesh_capabilities",
    "research_topology_capabilities",
]
