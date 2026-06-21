from __future__ import annotations
"""Distributed Event Bus — Redis/memory transport for federated agent mesh."""

import logging
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.mesh.node_registry import MeshNodeRegistry, default_local_node
from app.core.mesh.protocol import (
    DEFAULT_FANOUT_EVENTS,
    MESH_EVENTS_CHANNEL,
    MESH_SCHEMA_VERSION,
    region_filter_allows,
    topic_for_event,
)
from app.core.mesh.transport import MeshTransport, create_mesh_transport
from app.domain.mesh_schema import MeshEventEnvelope, MeshNodeDescriptor, MeshPublishRequest

logger = logging.getLogger(__name__)

RemoteHandler = Callable[[MeshEventEnvelope], None]

_DEDUP_WINDOW_SECONDS = 300
_DEDUP_MAX_SIZE = 5000


class DistributedEventBus:
    """Cross-node event propagation with loop-safe origin tracking."""

    def __init__(
        self,
        *,
        node_id: str,
        region: str = "CN",
        transport: MeshTransport | None = None,
        redis_url: str | None = None,
        registry: MeshNodeRegistry | None = None,
        fanout_events: frozenset[str] | None = None,
    ) -> None:
        self.node_id = node_id
        self.region = region.upper()
        self._transport = transport or create_mesh_transport(redis_url)
        self._registry = registry or MeshNodeRegistry()
        self._fanout_events = fanout_events or DEFAULT_FANOUT_EVENTS
        self._remote_handlers: list[RemoteHandler] = []
        self._recent_remote: deque[dict[str, Any]] = deque(maxlen=100)
        self._lock = threading.Lock()
        self._started = False
        self._dedup: dict[str, float] = {}
        self._metrics = {
            "published": 0,
            "received": 0,
            "dedup_skipped": 0,
            "loop_skipped": 0,
            "region_filtered": 0,
            "handler_errors": 0,
            "last_publish_at": None,
            "last_receive_at": None,
        }
        self._local_node = self._registry.register(
            default_local_node(node_id=node_id, region=region)
        )

    @property
    def transport_backend(self) -> str:
        return self._transport.backend

    @property
    def local_node(self) -> MeshNodeDescriptor:
        return self._local_node

    def start(self) -> None:
        if self._started:
            return
        self._transport.subscribe(MESH_EVENTS_CHANNEL, self._on_transport_message)
        for event_name in self._fanout_events:
            self._transport.subscribe(topic_for_event(event_name), self._on_transport_message)
        self._transport.start()
        self._started = True
        logger.info(
            "DistributedEventBus started node=%s region=%s backend=%s",
            self.node_id,
            self.region,
            self.transport_backend,
        )

    def stop(self) -> None:
        if not self._started:
            return
        self._transport.stop()
        self._registry.unregister(self.node_id)
        self._started = False

    def should_fanout(self, event_name: str) -> bool:
        return event_name in self._fanout_events

    def publish_envelope(self, envelope: MeshEventEnvelope) -> bool:
        channel = envelope.topic or topic_for_event(envelope.event_name)
        body = envelope.model_dump(mode="json")
        ok = self._transport.publish(channel, body)
        if ok:
            self._metrics["published"] += 1
            self._metrics["last_publish_at"] = datetime.now(timezone.utc).isoformat()
            self._recent_remote.appendleft(
                {"direction": "outbound", "envelope": body, "channel": channel}
            )
        return ok

    def publish(
        self,
        request: MeshPublishRequest,
        *,
        origin_node_id: str | None = None,
    ) -> dict[str, Any]:
        envelope = MeshEventEnvelope(
            schema_version=MESH_SCHEMA_VERSION,
            envelope_id=str(uuid.uuid4()),
            topic=request.topic or topic_for_event(request.event_name),
            event_name=request.event_name,
            origin_node_id=origin_node_id or self.node_id,
            origin_region=self.region,
            target_regions=request.target_regions,
            priority=request.priority,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=request.payload,
        )
        ok = self.publish_envelope(envelope)
        return {"ok": ok, "envelope_id": envelope.envelope_id, "topic": envelope.topic}

    def publish_local_event(self, event_name: str, payload: dict[str, Any], *, priority: int = 10) -> bool:
        req = MeshPublishRequest(
            event_name=event_name,
            payload=payload,
            priority=priority,
        )
        return bool(self.publish(req).get("ok"))

    def on_remote(self, handler: RemoteHandler) -> None:
        with self._lock:
            if handler not in self._remote_handlers:
                self._remote_handlers.append(handler)

    def list_peers(self) -> list[dict[str, Any]]:
        return [n.model_dump(mode="json") for n in self._registry.list_nodes()]

    def get_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": MESH_SCHEMA_VERSION,
            "node_id": self.node_id,
            "region": self.region,
            "transport": self.transport_backend,
            "fanout_events": sorted(self._fanout_events),
            "local_node": self._local_node.model_dump(mode="json"),
            "peer_count": len(self.list_peers()),
            "metrics": dict(self._metrics),
        }

    def list_recent_remote(self, *, limit: int = 30) -> list[dict[str, Any]]:
        lim = min(max(1, limit), 100)
        return list(self._recent_remote)[:lim]

    def _is_duplicate(self, envelope_id: str) -> bool:
        if not envelope_id:
            return False
        now = time.monotonic()
        with self._lock:
            self._cleanup_dedup(now)
            if envelope_id in self._dedup:
                return True
            self._dedup[envelope_id] = now
        return False

    def _cleanup_dedup(self, now: float) -> None:
        cutoff = now - _DEDUP_WINDOW_SECONDS
        expired = [k for k, ts in self._dedup.items() if ts < cutoff]
        for k in expired:
            del self._dedup[k]
        if len(self._dedup) > _DEDUP_MAX_SIZE:
            sorted_keys = sorted(self._dedup, key=lambda k: self._dedup[k])
            for k in sorted_keys[: len(sorted_keys) // 2]:
                del self._dedup[k]

    def _on_transport_message(self, channel: str, data: dict[str, Any]) -> None:
        self._metrics["received"] += 1
        self._metrics["last_receive_at"] = datetime.now(timezone.utc).isoformat()

        envelope_id = data.get("envelope_id", "")
        if self._is_duplicate(envelope_id):
            self._metrics["dedup_skipped"] += 1
            return

        try:
            envelope = MeshEventEnvelope.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            logger.debug("mesh envelope parse skip: %s", exc)
            return
        if envelope.origin_node_id == self.node_id:
            self._metrics["loop_skipped"] += 1
            return
        if not region_filter_allows(envelope.target_regions, self.region):
            self._metrics["region_filtered"] += 1
            return
        self._recent_remote.appendleft(
            {"direction": "inbound", "envelope": envelope.model_dump(mode="json"), "channel": channel}
        )
        with self._lock:
            handlers = list(self._remote_handlers)
        for handler in handlers:
            try:
                handler(envelope)
            except Exception as exc:  # noqa: BLE001
                self._metrics["handler_errors"] += 1
                logger.warning("mesh remote handler: %s", exc)


_distributed_bus: DistributedEventBus | None = None
_bridge_started = False


def get_distributed_event_bus() -> DistributedEventBus | None:
    return _distributed_bus


def configure_distributed_event_bus(bus: DistributedEventBus | None) -> None:
    global _distributed_bus
    _distributed_bus = bus


__all__ = [
    "DistributedEventBus",
    "get_distributed_event_bus",
    "configure_distributed_event_bus",
]
