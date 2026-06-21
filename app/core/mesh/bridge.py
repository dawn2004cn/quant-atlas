from __future__ import annotations
"""Bridge local EventBus ↔ DistributedEventBus (Quant Atlas 9.0 Step One)."""

import logging
from typing import Any

from app.core.event_bus import Event, get_event_bus
from app.core.mesh.distributed_event_bus import (
    DistributedEventBus,
    configure_distributed_event_bus,
    get_distributed_event_bus,
)
from app.core.mesh.node_registry import MeshNodeRegistry
from app.core.mesh.transport import create_mesh_transport
from app.core.runtime_config import get_runtime_bool
from app.domain.mesh_schema import MeshEventEnvelope

logger = logging.getLogger(__name__)

_bridge_handlers: list[Any] = []
_mesh_started = False


def _event_payload(event: Event) -> dict[str, Any]:
    return {
        key: value
        for key, value in vars(event).items()
        if key not in ("timestamp", "source", "priority", "ttl_seconds")
    }


def _make_outbound_handler(bus: DistributedEventBus):
    def _forward(event: Event) -> None:
        if not bus.should_fanout(event.__class__.__name__):
            return
        bus.publish_local_event(
            event.__class__.__name__,
            _event_payload(event),
            priority=getattr(event, "priority", 10),
        )

    return _forward


def _inject_remote(envelope: MeshEventEnvelope) -> None:
    from app.core.event_bus import MeshForwardedEvent

    get_event_bus().publish(
        MeshForwardedEvent(
            source=f"mesh:{envelope.origin_node_id}",
            priority=envelope.priority,
            original_event=envelope.event_name,
            origin_node_id=envelope.origin_node_id,
            origin_region=envelope.origin_region,
            envelope_id=envelope.envelope_id,
            payload=envelope.payload,
        )
    )


def start_mesh_bridge(
    *,
    redis_url: str | None = None,
    node_id: str | None = None,
    region: str | None = None,
    force: bool = False,
) -> DistributedEventBus | None:
    """Start federated mesh bridge when MESH_ENABLED is true."""
    global _mesh_started, _bridge_handlers

    if _mesh_started and not force:
        return get_distributed_event_bus()

    from app.core.strategic_sunset import feature_enabled

    enabled = get_runtime_bool("MESH_ENABLED", False)
    if not enabled and not force:
        logger.debug("mesh bridge disabled (MESH_ENABLED=false)")
        return None
    if not feature_enabled("federated_mesh") and not force:
        logger.debug("mesh bridge disabled (FEATURE_FEDERATED_MESH=false)")
        return None

    from app.core.runtime_config import get_runtime

    nid = (node_id or get_runtime("MESH_NODE_ID", "cn-gateway-1")).strip()
    reg = (region or get_runtime("MESH_REGION", "CN")).strip().upper()
    url = redis_url
    if url is None:
        url = get_runtime("MESH_REDIS_URL", "") or get_runtime("TASK_MESSAGE_REDIS_URL", "")
    mesh_transport = get_runtime("MESH_TRANSPORT", "redis")
    nats_url = get_runtime("MESH_NATS_URL", "nats://127.0.0.1:4222")

    redis_client = None
    if (url or "").strip():
        try:
            import redis

            redis_client = redis.Redis.from_url(url, decode_responses=True)
            redis_client.ping()
        except Exception as exc:  # noqa: BLE001
            logger.warning("mesh redis registry unavailable: %s", exc)
            redis_client = None

    transport = create_mesh_transport(
        url,
        force_memory=force and not url and mesh_transport != "nats",
        transport_kind=mesh_transport,
        nats_url=nats_url,
    )
    registry = MeshNodeRegistry(redis_client=redis_client)
    bus = DistributedEventBus(
        node_id=nid,
        region=reg,
        transport=transport,
        registry=registry,
        redis_url=url,
    )
    bus.on_remote(_inject_remote)
    bus.start()

    local_bus = get_event_bus()
    event_types = _resolve_fanout_event_types(bus)
    handlers: list[Any] = []
    for event_type in event_types:
        handler = _make_outbound_handler(bus)
        local_bus.subscribe(event_type, handler)
        handlers.append((event_type, handler))

    configure_distributed_event_bus(bus)
    _bridge_handlers = handlers
    _mesh_started = True
    logger.info("mesh bridge active node=%s region=%s", nid, reg)
    return bus


def stop_mesh_bridge() -> None:
    global _mesh_started, _bridge_handlers
    bus = get_distributed_event_bus()
    if bus is not None:
        bus.stop()
    local_bus = get_event_bus()
    for event_type, handler in _bridge_handlers:
        local_bus.unsubscribe(event_type, handler)
    _bridge_handlers = []
    configure_distributed_event_bus(None)
    _mesh_started = False


def _resolve_fanout_event_types(bus: DistributedEventBus) -> list[type[Event]]:
    from app.core.event_bus import (
        AnalysisStaleEvent,
        ArbiterConsensusEvent,
        CorrectionIntentEvent,
        CrossTeamSiteAlertEvent,
        DebateRoundEvent,
        MarketDataUpdatedEvent,
        MetaArbiterActivatedEvent,
        TradeExecutedEvent,
        TruthDeviationEvent,
        WorkflowCompletedEvent,
    )

    mapping = {
        "DebateRoundEvent": DebateRoundEvent,
        "ArbiterConsensusEvent": ArbiterConsensusEvent,
        "MetaArbiterActivatedEvent": MetaArbiterActivatedEvent,
        "CrossTeamSiteAlertEvent": CrossTeamSiteAlertEvent,
        "WorkflowCompletedEvent": WorkflowCompletedEvent,
        "MarketDataUpdatedEvent": MarketDataUpdatedEvent,
        "TradeExecutedEvent": TradeExecutedEvent,
        "TruthDeviationEvent": TruthDeviationEvent,
        "AnalysisStaleEvent": AnalysisStaleEvent,
        "CorrectionIntentEvent": CorrectionIntentEvent,
    }
    out: list[type[Event]] = []
    for name in bus._fanout_events:
        cls = mapping.get(name)
        if cls is not None:
            out.append(cls)
    return out


__all__ = ["start_mesh_bridge", "stop_mesh_bridge"]
