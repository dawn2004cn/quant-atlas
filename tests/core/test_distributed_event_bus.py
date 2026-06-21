from __future__ import annotations

import threading

from app.core.event_bus import DebateRoundEvent, MeshForwardedEvent, get_event_bus
from app.core.mesh.bridge import start_mesh_bridge, stop_mesh_bridge
from app.core.mesh.distributed_event_bus import DistributedEventBus
from app.core.mesh.node_registry import MeshNodeRegistry
from app.core.mesh.transport import MemoryMeshTransport, create_mesh_transport
from app.domain.mesh_schema import MeshPublishRequest


def test_distributed_bus_loop_prevention() -> None:
    transport = MemoryMeshTransport()
    bus_a = DistributedEventBus(node_id="node-a", region="CN", transport=transport)
    bus_b = DistributedEventBus(node_id="node-b", region="US", transport=transport)
    bus_a.start()
    bus_b.start()

    received: list[str] = []

    def _on_remote(envelope) -> None:
        received.append(envelope.event_name)

    bus_b.on_remote(_on_remote)
    bus_a.publish(
        MeshPublishRequest(event_name="DebateRoundEvent", payload={"symbol": "600519"})
    )
    assert received == ["DebateRoundEvent"]

    bus_a.publish(
        MeshPublishRequest(
            event_name="DebateRoundEvent",
            payload={"symbol": "600519"},
            target_regions=["EU"],
        )
    )
    assert received == ["DebateRoundEvent"]

    stop_mesh_bridge()
    bus_a.stop()
    bus_b.stop()


def test_mesh_bridge_injects_mesh_forwarded_event() -> None:
    get_event_bus().clear()
    transport = MemoryMeshTransport()
    registry = MeshNodeRegistry()
    bus_local = DistributedEventBus(
        node_id="cn-1",
        region="CN",
        transport=transport,
        registry=registry,
    )
    bus_remote = DistributedEventBus(
        node_id="us-1",
        region="US",
        transport=transport,
        registry=registry,
    )
    bus_local.start()
    bus_remote.start()

    captured: list[MeshForwardedEvent] = []
    gate = threading.Event()

    def _capture(evt: MeshForwardedEvent) -> None:
        captured.append(evt)
        gate.set()

    get_event_bus().subscribe(MeshForwardedEvent, _capture)
    bus_remote.on_remote(
        lambda env: get_event_bus().publish(
            MeshForwardedEvent(
                source=f"mesh:{env.origin_node_id}",
                original_event=env.event_name,
                origin_node_id=env.origin_node_id,
                origin_region=env.origin_region,
                envelope_id=env.envelope_id,
                payload=env.payload,
            )
        )
    )

    bus_local.publish_local_event(
        "DebateRoundEvent",
        {"symbol": "sz000001", "stance": "bullish"},
    )
    gate.wait(timeout=2.0)
    assert len(captured) == 1
    assert captured[0].original_event == "DebateRoundEvent"
    assert captured[0].origin_node_id == "cn-1"
    assert captured[0].payload.get("symbol") == "sz000001"

    bus_local.stop()
    bus_remote.stop()
    get_event_bus().clear()


def test_mesh_transport_nats_fallback() -> None:
    transport = create_mesh_transport(
        None,
        transport_kind="nats",
        nats_url="nats://127.0.0.1:42229",
    )
    assert transport.backend in ("nats", "nats_unavailable", "memory")


def test_start_mesh_bridge_force_memory() -> None:
    stop_mesh_bridge()
    get_event_bus().clear()
    bus = start_mesh_bridge(force=True, node_id="test-node", region="CN")
    assert bus is not None
    manifest = bus.get_manifest()
    assert manifest["node_id"] == "test-node"
    assert manifest["transport"] == "memory"
    stop_mesh_bridge()
    get_event_bus().clear()
