from __future__ import annotations
"""Mesh node registry — local cache with optional Redis peer discovery."""

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from app.core.mesh.protocol import REDIS_NODES_KEY, REDIS_NODE_TTL_SECONDS
from app.domain.mesh_schema import MeshNodeDescriptor, MeshRegion

logger = logging.getLogger(__name__)


class MeshNodeRegistry:
    def __init__(self, *, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._local: dict[str, MeshNodeDescriptor] = {}
        self._lock = threading.Lock()

    def register(self, node: MeshNodeDescriptor) -> MeshNodeDescriptor:
        now = datetime.now(timezone.utc).isoformat()
        updated = node.model_copy(update={"last_heartbeat": now, "status": "online"})
        with self._lock:
            self._local[updated.node_id] = updated
        self._persist_redis(updated)
        return updated

    def heartbeat(self, node_id: str) -> MeshNodeDescriptor | None:
        with self._lock:
            node = self._local.get(node_id)
        if node is None:
            return None
        return self.register(node)

    def unregister(self, node_id: str) -> None:
        with self._lock:
            self._local.pop(node_id, None)
        if self._redis is not None:
            try:
                self._redis.hdel(REDIS_NODES_KEY, node_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("mesh registry hdel: %s", exc)

    def list_nodes(self, *, include_remote: bool = True) -> list[MeshNodeDescriptor]:
        with self._lock:
            nodes = {n.node_id: n for n in self._local.values()}
        if include_remote and self._redis is not None:
            try:
                raw = self._redis.hgetall(REDIS_NODES_KEY) or {}
                for node_id, blob in raw.items():
                    nid = node_id.decode() if isinstance(node_id, bytes) else str(node_id)
                    if nid in nodes:
                        continue
                    text = blob.decode() if isinstance(blob, bytes) else str(blob)
                    try:
                        data = json.loads(text)
                        nodes[nid] = MeshNodeDescriptor.model_validate(data)
                    except (json.JSONDecodeError, ValueError):
                        continue
            except Exception as exc:  # noqa: BLE001
                logger.warning("mesh registry list remote: %s", exc)
        return sorted(nodes.values(), key=lambda n: n.node_id)

    def get_local_node(self, node_id: str) -> MeshNodeDescriptor | None:
        with self._lock:
            return self._local.get(node_id)

    def _persist_redis(self, node: MeshNodeDescriptor) -> None:
        if self._redis is None:
            return
        try:
            payload = node.model_dump(mode="json")
            self._redis.hset(REDIS_NODES_KEY, node.node_id, json.dumps(payload, ensure_ascii=False))
            self._redis.expire(REDIS_NODES_KEY, REDIS_NODE_TTL_SECONDS * 10)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mesh registry persist: %s", exc)


def default_local_node(
    *,
    node_id: str,
    region: str = "CN",
    roles: list[str] | None = None,
) -> MeshNodeDescriptor:
    from app.domain.mesh_schema import MeshNodeRole

    role_enums: list[MeshNodeRole] = [MeshNodeRole.GATEWAY]
    for r in roles or []:
        try:
            role_enums.append(MeshNodeRole(r))
        except ValueError:
            logger.warning("Suppressed exception", exc_info=True)
            pass
    try:
        region_enum = MeshRegion(region.upper())
    except ValueError:
        region_enum = MeshRegion.CN
    capabilities = ["event_fanout", "federated_agents"]
    try:
        from app.core.mesh.agent_discovery import build_local_mesh_capabilities

        capabilities = build_local_mesh_capabilities()
    except Exception as exc:  # noqa: BLE001
        logger.debug("default_local_node capabilities: %s", exc)
    return MeshNodeDescriptor(
        node_id=node_id,
        region=region_enum,
        roles=role_enums,
        capabilities=capabilities,
        agent_topology_id="research_default",
        endpoint="",
        status="online",
    )


__all__ = ["MeshNodeRegistry", "default_local_node"]
