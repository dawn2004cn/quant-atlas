from __future__ import annotations

import threading

from app.core.event_bus import MeshForwardedEvent, get_event_bus
from app.core.mesh.distributed_event_bus import DistributedEventBus
from app.core.mesh.node_registry import MeshNodeRegistry
from app.core.mesh.transport import MemoryMeshTransport


def test_mesh_two_nodes_cross_region_fanout() -> None:
    """CN gateway publishes; US gateway receives via shared in-memory transport."""
    transport = MemoryMeshTransport()
    registry = MeshNodeRegistry()

    bus_cn = DistributedEventBus(
        node_id="cn-gateway-1",
        region="CN",
        transport=transport,
        registry=registry,
    )
    bus_us = DistributedEventBus(
        node_id="us-gateway-1",
        region="US",
        transport=transport,
        registry=registry,
    )
    bus_cn.start()
    bus_us.start()

    captured: list[MeshForwardedEvent] = []
    gate = threading.Event()

    def _on_remote(envelope) -> None:
        get_event_bus().publish(
            MeshForwardedEvent(
                source=f"mesh:{envelope.origin_node_id}",
                original_event=envelope.event_name,
                origin_node_id=envelope.origin_node_id,
                origin_region=envelope.origin_region,
                envelope_id=envelope.envelope_id,
                payload=envelope.payload,
            )
        )

    bus_us.on_remote(_on_remote)

    def _capture(evt: MeshForwardedEvent) -> None:
        captured.append(evt)
        gate.set()

    get_event_bus().subscribe(MeshForwardedEvent, _capture)

    bus_cn.publish_local_event(
        "TruthDeviationEvent",
        {
            "symbol": "600519",
            "market": "CN",
            "diff_pct": 1.2,
            "outliers": ["Qlib"],
        },
    )

    gate.wait(timeout=2.0)
    assert len(captured) == 1
    assert captured[0].original_event == "TruthDeviationEvent"
    assert captured[0].origin_node_id == "cn-gateway-1"
    assert captured[0].origin_region == "CN"
    assert captured[0].payload.get("symbol") == "600519"

    bus_cn.stop()
    bus_us.stop()
    get_event_bus().clear()


def test_mesh_peer_registry_lists_both_nodes() -> None:
    transport = MemoryMeshTransport()
    registry = MeshNodeRegistry()
    bus_a = DistributedEventBus(node_id="node-a", region="CN", transport=transport, registry=registry)
    bus_b = DistributedEventBus(node_id="node-b", region="US", transport=transport, registry=registry)
    bus_a.start()
    bus_b.start()

    peers = {p["node_id"] for p in bus_a.list_peers()}
    assert "node-a" in peers
    assert "node-b" in peers

    bus_a.stop()
    bus_b.stop()
