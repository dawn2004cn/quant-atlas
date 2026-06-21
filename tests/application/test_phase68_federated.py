"""Phase 68: Federated deployment heartbeat and FedAvg rounds."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.system.services.institution_tier_service import FederatedDeploymentService


@pytest.fixture
def fed_svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FederatedDeploymentService:
    store = tmp_path / "federated"
    store.mkdir()
    svc = FederatedDeploymentService()
    monkeypatch.setattr(svc, "_store", store)
    monkeypatch.setattr(svc, "_updates_file", store / "model_updates.jsonl")
    monkeypatch.setattr(svc, "_nodes_file", store / "deployment_nodes.jsonl")
    monkeypatch.setattr(svc, "_config_file", store / "deployment_config.json")
    monkeypatch.setattr(svc, "_models_dir", store / "aggregated_models")
    svc._models_dir.mkdir(parents=True, exist_ok=True)
    return svc


def test_node_heartbeat_and_stale_detection(fed_svc: FederatedDeploymentService, monkeypatch: pytest.MonkeyPatch) -> None:
    fed_svc.set_deployment_config({"heartbeat_timeout_sec": 60})
    fed_svc.register_node("n1", "Node 1")
    fed_svc.heartbeat("n1", metadata={"region": "CN"})
    nodes = fed_svc.list_nodes()
    assert len(nodes) == 1
    assert nodes[0]["stale"] is False

    old_ts = "2000-01-01T00:00:00+00:00"
    nodes_map = fed_svc._load_nodes_map()
    nodes_map["n1"].last_sync = old_ts
    fed_svc._write_nodes(nodes_map)
    stale_nodes = fed_svc.list_nodes()
    assert stale_nodes[0]["stale"] is True


def test_fedavg_round_requires_min_nodes(fed_svc: FederatedDeploymentService) -> None:
    fed_svc.set_deployment_config({"min_nodes_for_aggregate": 2, "heartbeat_timeout_sec": 3600})
    fed_svc.register_node("n1", "A")
    fed_svc.receive_update("n1", "m1", {"w1": 0.1}, 0.01)
    result = fed_svc.run_fedavg_round("m1")
    assert result.ok is False
    assert "need 2 nodes" in result.message


def test_fedavg_round_success(fed_svc: FederatedDeploymentService) -> None:
    fed_svc.set_deployment_config({"min_nodes_for_aggregate": 2, "heartbeat_timeout_sec": 3600})
    fed_svc.register_node("n1", "A")
    fed_svc.register_node("n2", "B")
    fed_svc.receive_update("n1", "alpha_v1", {"w_mom": 0.10, "w_val": 0.20}, 0.01)
    fed_svc.receive_update("n2", "alpha_v1", {"w_mom": 0.14, "w_val": 0.16}, 0.02)
    result = fed_svc.run_fedavg_round("alpha_v1")
    assert result.ok is True
    assert result.weights["w_mom"] == pytest.approx(0.12, abs=1e-4)
    assert result.weights["w_val"] == pytest.approx(0.18, abs=1e-4)
    saved = fed_svc.get_aggregated_model("alpha_v1")
    assert saved is not None
    assert saved["weights"]["w_mom"] == pytest.approx(0.12, abs=1e-4)


def test_cluster_status(fed_svc: FederatedDeploymentService) -> None:
    fed_svc.register_node("n1", "A")
    fed_svc.receive_update("n1", "m1", {"w": 1.0}, 0.0)
    status = fed_svc.get_cluster_status()
    assert status.total_nodes == 1
    assert status.pending_updates == 1
    assert "m1" in status.models_with_updates
