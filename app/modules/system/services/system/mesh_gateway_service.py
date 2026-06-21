from __future__ import annotations
"""Mesh gateway — federated agent cluster operations (Quant Atlas 9.0)."""

import logging
from typing import Any

from app.core.mesh.agent_discovery import AgentDiscoveryProtocol
from app.core.mesh.bridge import start_mesh_bridge, stop_mesh_bridge
from app.core.mesh.distributed_event_bus import DistributedEventBus, get_distributed_event_bus
from app.core.runtime_config import get_runtime_bool
from app.domain.mesh_schema import MeshPublishRequest

logger = logging.getLogger(__name__)


class MeshGatewayService:
    """Expose mesh manifest, peer registry, and manual publish for ops/debug."""

    def __init__(self, *, redis_url: str | None = None) -> None:
        self._redis_url = redis_url

    def ensure_started(self) -> DistributedEventBus | None:
        bus = get_distributed_event_bus()
        if bus is not None:
            return bus
        if not get_runtime_bool("MESH_ENABLED", False):
            return None
        return start_mesh_bridge(redis_url=self._redis_url)

    def get_manifest(self) -> dict[str, Any]:
        bus = self.ensure_started()
        if bus is None:
            return {
                "ok": True,
                "enabled": False,
                "message": "mesh_disabled",
            }
        manifest = bus.get_manifest()
        manifest["ok"] = True
        manifest["enabled"] = True
        return manifest

    def list_nodes(self) -> dict[str, Any]:
        bus = self.ensure_started()
        if bus is None:
            return {"ok": True, "enabled": False, "nodes": [], "count": 0}
        nodes = bus.list_peers()
        return {"ok": True, "enabled": True, "nodes": nodes, "count": len(nodes)}

    def publish(self, body: dict[str, Any]) -> dict[str, Any]:
        bus = self.ensure_started()
        if bus is None:
            return {"ok": False, "error": "mesh_disabled"}
        try:
            req = MeshPublishRequest.model_validate(body)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"invalid_request:{exc}"}
        result = bus.publish(req)
        result["ok"] = bool(result.get("ok"))
        return result

    def list_recent(self, *, limit: int = 30) -> dict[str, Any]:
        bus = get_distributed_event_bus()
        if bus is None:
            return {"ok": True, "enabled": False, "events": [], "count": 0}
        events = bus.list_recent_remote(limit=limit)
        return {"ok": True, "enabled": True, "events": events, "count": len(events)}

    def discover_agents(
        self,
        *,
        role: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        """Cross-node agent discovery — local research topology + mesh registry."""
        bus = get_distributed_event_bus() or self.ensure_started()
        registry = bus._registry if bus is not None else None  # noqa: SLF001
        protocol = AgentDiscoveryProtocol(registry=registry)
        result = protocol.discover(role=role, region=region)
        result["mesh_enabled"] = bus is not None
        return result

    def restart_bridge(self) -> dict[str, Any]:
        stop_mesh_bridge()
        bus = start_mesh_bridge(redis_url=self._redis_url, force=True)
        if bus is None:
            return {"ok": False, "error": "mesh_start_failed"}
        return {"ok": True, "node_id": bus.node_id, "transport": bus.transport_backend}

    def health(self) -> dict[str, Any]:
        from app.core.cluster_event_bus import get_cluster_event_bus

        return get_cluster_event_bus().health()

    def list_browser_nodes(self) -> dict[str, Any]:
        from app.core.mesh.browser_node_adapter import get_browser_node_adapter

        adapter = get_browser_node_adapter()
        if adapter is None:
            return {"ok": True, "enabled": False, "browser_nodes": [], "count": 0}
        nodes = adapter.list_browser_nodes()
        manifest = adapter.get_manifest()
        return {
            "ok": True,
            "enabled": True,
            "browser_nodes": nodes,
            "count": len(nodes),
            "manifest": manifest,
        }


__all__ = ["MeshGatewayService"]
