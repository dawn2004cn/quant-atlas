from __future__ import annotations
"""Cluster EventBus facade — local EventBus + optional distributed mesh (Redis/NATS)."""

from typing import Any

from app.core.event_bus import EventBus, get_event_bus
from app.core.logger import get_logger
from app.core.mesh.distributed_event_bus import DistributedEventBus, get_distributed_event_bus
from app.core.runtime_config import get_runtime, get_runtime_bool
from app.core.strategic_sunset import feature_enabled

logger = get_logger(__name__)

_facade: ClusterEventBusFacade | None = None


class ClusterEventBusFacade:
    """Unified entry for in-process EventBus and cross-node mesh fan-out."""

    def local(self) -> EventBus:
        return get_event_bus()

    def distributed(self) -> DistributedEventBus | None:
        return get_distributed_event_bus()

    def resolve_mode(self) -> str:
        explicit = (get_runtime("EVENT_BUS_CLUSTER_MODE", "auto") or "auto").strip().lower()
        if explicit in ("local", "off", "disabled"):
            return "local"
        if explicit in ("mesh", "cluster", "distributed"):
            return "cluster"
        if get_distributed_event_bus() is not None:
            return "cluster"
        if get_runtime_bool("MESH_ENABLED", False) and feature_enabled("federated_mesh"):
            return "cluster_pending"
        return "local"

    def is_cluster_active(self) -> bool:
        return self.distributed() is not None

    def ensure_cluster(
        self,
        *,
        redis_url: str | None = None,
        force: bool = False,
    ) -> DistributedEventBus | None:
        """Start mesh bridge when cluster mode is enabled (idempotent)."""
        mode = self.resolve_mode()
        if mode == "local" and not force:
            return None
        existing = self.distributed()
        if existing is not None and not force:
            return existing
        from app.core.mesh.bridge import start_mesh_bridge

        url = redis_url
        if url is None:
            url = get_runtime("MESH_REDIS_URL", "") or get_runtime("TASK_MESSAGE_REDIS_URL", "")
        bus = start_mesh_bridge(redis_url=url or None, force=force)
        if bus is not None:
            logger.info("cluster event bus active transport=%s", bus.transport_backend)
        return bus

    def stop_cluster(self) -> None:
        from app.core.mesh.bridge import stop_mesh_bridge

        stop_mesh_bridge()

    def manifest(self) -> dict[str, Any]:
        local = self.local()
        dist = self.distributed()
        out: dict[str, Any] = {
            "ok": True,
            "mode": self.resolve_mode(),
            "cluster_active": dist is not None,
            "local": {
                "subscribers": local.list_subscribers(),
                "recent_count": len(local.list_recent_events(limit=200)),
            },
        }
        if dist is not None:
            out["distributed"] = dist.get_manifest()
            out["peers"] = dist.list_peers()
            transport = dist._transport
            if hasattr(transport, "health"):
                out["transport_health"] = transport.health
        else:
            out["distributed"] = None
            out["hint"] = "Set MESH_ENABLED=1 and EVENT_BUS_CLUSTER_MODE=auto|cluster to enable"
        return out

    def health(self) -> dict[str, Any]:
        dist = self.distributed()
        if dist is None:
            return {
                "cluster_active": False,
                "mode": self.resolve_mode(),
                "transport": "none",
            }
        transport = dist._transport
        transport_health = transport.health if hasattr(transport, "health") else {}
        return {
            "cluster_active": True,
            "mode": self.resolve_mode(),
            "node_id": dist.node_id,
            "region": dist.region,
            "transport": dist.transport_backend,
            "peer_count": len(dist.list_peers()),
            "transport_health": transport_health,
            "metrics": dist._metrics,
        }

    def publish_remote(
        self,
        event_name: str,
        payload: dict[str, Any],
        *,
        priority: int = 10,
    ) -> dict[str, Any]:
        """Publish directly to distributed mesh (bypasses local handlers)."""
        dist = self.distributed() or self.ensure_cluster()
        if dist is None:
            return {"ok": False, "error": "cluster_inactive"}
        ok = dist.publish_local_event(event_name, payload, priority=priority)
        return {"ok": bool(ok), "event_name": event_name}


def get_cluster_event_bus() -> ClusterEventBusFacade:
    global _facade
    if _facade is None:
        _facade = ClusterEventBusFacade()
    return _facade


__all__ = ["ClusterEventBusFacade", "get_cluster_event_bus"]
