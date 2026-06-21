"""Cluster EventBus facade — local + mesh manifest."""

from __future__ import annotations

import pytest

from app.core.cluster_event_bus import ClusterEventBusFacade, get_cluster_event_bus
from app.core.event_bus import ServiceStartedEvent, get_event_bus
from app.core.mesh.bridge import stop_mesh_bridge


@pytest.fixture(autouse=True)
def _reset_mesh():
    stop_mesh_bridge()
    yield
    stop_mesh_bridge()


def test_resolve_mode_local_by_default(monkeypatch):
    monkeypatch.delenv("MESH_ENABLED", raising=False)
    monkeypatch.setenv("EVENT_BUS_CLUSTER_MODE", "local")
    facade = ClusterEventBusFacade()
    assert facade.resolve_mode() == "local"
    assert facade.is_cluster_active() is False


def test_manifest_includes_local_subscribers():
    bus = get_event_bus()
    bus.subscribe(ServiceStartedEvent, lambda _e: None)
    manifest = get_cluster_event_bus().manifest()
    assert manifest["ok"] is True
    assert "ServiceStartedEvent" in manifest["local"]["subscribers"]
    assert manifest["cluster_active"] is False


def test_ensure_cluster_starts_mesh(monkeypatch):
    monkeypatch.setenv("MESH_ENABLED", "1")
    monkeypatch.setenv("EVENT_BUS_CLUSTER_MODE", "cluster")
    monkeypatch.setenv("MESH_TRANSPORT", "memory")
    facade = ClusterEventBusFacade()
    dist = facade.ensure_cluster(force=True)
    assert dist is not None
    assert facade.is_cluster_active() is True
    m = facade.manifest()
    assert m["cluster_active"] is True
    assert m["distributed"] is not None


def test_publish_remote_when_cluster_active(monkeypatch):
    monkeypatch.setenv("MESH_ENABLED", "1")
    monkeypatch.setenv("MESH_TRANSPORT", "memory")
    facade = ClusterEventBusFacade()
    facade.ensure_cluster(force=True)
    out = facade.publish_remote("cluster.test", {"x": 1})
    assert out["ok"] is True
    assert out["event_name"] == "cluster.test"
