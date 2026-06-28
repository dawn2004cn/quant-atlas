from __future__ import annotations

"""BrowserNodeAdapter — bridges SocketIO browser clients into the federated mesh (9.0 Fabric)."""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.core.mesh.node_registry import MeshNodeRegistry
from app.domain.mesh_schema import MeshNodeDescriptor, MeshNodeRole, MeshRegion

logger = logging.getLogger(__name__)

_BROWSER_HEARTBEAT_INTERVAL = 30
_BROWSER_STALE_THRESHOLD = 90


class BrowserNodeAdapter:
    """Registers browser SocketIO clients as lightweight mesh nodes.

    Each connected browser session becomes a MeshNodeDescriptor with role
    BROWSER_CLIENT. The adapter tracks subscriptions and forwards relevant
    mesh events to the browser via SocketIO emit.
    """

    def __init__(
        self,
        *,
        registry: MeshNodeRegistry | None = None,
        emit_func: Any | None = None,
    ) -> None:
        self._registry = registry or MeshNodeRegistry()
        self._emit = emit_func
        self._nodes: dict[str, MeshNodeDescriptor] = {}
        self._subscriptions: dict[str, set[str]] = {}
        self._last_seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def register_browser(
        self,
        *,
        sid: str,
        user_id: str | int | None = None,
        room: str | None = None,
        capabilities: list[str] | None = None,
    ) -> MeshNodeDescriptor:
        node_id = f"browser-{sid[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        caps = list(capabilities or [])
        if "canvas_render" not in caps:
            caps.append("canvas_render")

        descriptor = MeshNodeDescriptor(
            node_id=node_id,
            region=MeshRegion.CLIENT,
            roles=[MeshNodeRole.BROWSER_CLIENT],
            capabilities=caps,
            endpoint=f"socketio://{sid}",
            status="online",
            last_heartbeat=now,
            user_id=str(user_id) if user_id else None,
            session_id=sid,
        )

        with self._lock:
            self._nodes[node_id] = descriptor
            self._subscriptions.setdefault(node_id, set())
            self._last_seen[node_id] = time.monotonic()

        try:
            self._registry.register(descriptor)
        except Exception as exc:
            logger.debug("browser node registry skip: %s", exc)

        logger.debug("browser node registered node=%s user=%s", node_id, user_id)
        return descriptor

    def unregister_browser(self, sid: str) -> None:
        node_id = f"browser-{sid[:12]}"
        with self._lock:
            self._nodes.pop(node_id, None)
            self._subscriptions.pop(node_id, None)
            self._last_seen.pop(node_id, None)
        try:
            self._registry.unregister(node_id)
        except Exception as exc:
            logger.debug("browser node unregister skip: %s", exc)

    def heartbeat(self, sid: str) -> None:
        node_id = f"browser-{sid[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            node = self._nodes.get(node_id)
            if node is not None:
                node.last_heartbeat = now
                node.status = "online"
            self._last_seen[node_id] = time.monotonic()

    def subscribe(self, sid: str, channel: str) -> None:
        node_id = f"browser-{sid[:12]}"
        with self._lock:
            self._subscriptions.setdefault(node_id, set()).add(channel)

    def unsubscribe(self, sid: str, channel: str) -> None:
        node_id = f"browser-{sid[:12]}"
        with self._lock:
            subs = self._subscriptions.get(node_id)
            if subs:
                subs.discard(channel)

    def emit_to_browser(self, sid: str, event: str, data: dict[str, Any]) -> bool:
        if self._emit is None:
            return False
        try:
            self._emit(event, data, room=sid)
            return True
        except Exception as exc:
            logger.debug("browser emit failed: %s", exc)
            return False

    def broadcast_event(
        self,
        event: str,
        data: dict[str, Any],
        *,
        channel: str | None = None,
        user_id: str | int | None = None,
    ) -> int:
        delivered = 0
        with self._lock:
            targets = list(self._nodes.items())
            subs_snapshot = {k: set(v) for k, v in self._subscriptions.items()}

        for node_id, node in targets:
            if user_id is not None and node.user_id != str(user_id):
                continue
            if channel is not None:
                node_subs = subs_snapshot.get(node_id, set())
                if channel not in node_subs and "*" not in node_subs:
                    continue
            sid = node.session_id
            if sid and self.emit_to_browser(sid, event, data):
                delivered += 1
        return delivered

    def list_browser_nodes(self) -> list[dict[str, Any]]:
        with self._lock:
            return [n.model_dump(mode="json") for n in self._nodes.values()]

    def prune_stale(self) -> int:
        now = time.monotonic()
        stale_ids: list[str] = []
        with self._lock:
            for node_id, last in list(self._last_seen.items()):
                if now - last > _BROWSER_STALE_THRESHOLD:
                    stale_ids.append(node_id)
            for node_id in stale_ids:
                self._nodes.pop(node_id, None)
                self._subscriptions.pop(node_id, None)
                self._last_seen.pop(node_id, None)

        for node_id in stale_ids:
            try:
                self._registry.unregister(node_id)
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass
        return len(stale_ids)

    def get_manifest(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._nodes)
            online = sum(
                1 for n in self._nodes.values() if n.status == "online"
            )
            users = {n.user_id for n in self._nodes.values() if n.user_id}
        return {
            "browser_nodes": total,
            "online": online,
            "unique_users": len(users),
        }


_browser_adapter: BrowserNodeAdapter | None = None


def get_browser_node_adapter() -> BrowserNodeAdapter | None:
    return _browser_adapter


def configure_browser_node_adapter(adapter: BrowserNodeAdapter | None) -> None:
    global _browser_adapter
    _browser_adapter = adapter


__all__ = [
    "BrowserNodeAdapter",
    "get_browser_node_adapter",
    "configure_browser_node_adapter",
]
