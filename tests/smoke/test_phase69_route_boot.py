"""Phase 69: route boot hygiene and federated cluster scan."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.system.services.institution_tier_service import FederatedDeploymentService


def test_route_modules_preload_without_syntax_errors() -> None:
    from app.presentation.api.route_loader import preload_route_modules

    loaded = preload_route_modules()
    assert loaded >= 95


def test_decision_provenance_and_trade_plan_import() -> None:
    import app.presentation.api.routes_v1_decision_provenance as prov
    import app.presentation.api.routes_v1_trade_plan as trade_plan

    assert callable(prov.register_decision_provenance_routes)
    assert callable(trade_plan.register_trade_plan_routes)


def test_tokenized_and_provenance_blueprint_aliases() -> None:
    from app.presentation.api.routes_v1_tokenized_alpha import blueprint as token_bp
    from app.presentation.api.routes_v1_provenance import blueprint as prov_bp

    assert token_bp.url_prefix == "/alpha/tokens"
    assert prov_bp.url_prefix == "/provenance"


def test_federated_cluster_scan_marks_stale_inactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "federated"
    store.mkdir()
    svc = FederatedDeploymentService()
    monkeypatch.setattr(svc, "_store", store)
    monkeypatch.setattr(svc, "_nodes_file", store / "deployment_nodes.jsonl")
    monkeypatch.setattr(svc, "_config_file", store / "deployment_config.json")
    monkeypatch.setattr(svc, "_updates_file", store / "model_updates.jsonl")
    monkeypatch.setattr(svc, "_models_dir", store / "aggregated_models")
    svc._models_dir.mkdir(parents=True, exist_ok=True)

    svc.set_deployment_config({"heartbeat_timeout_sec": 60})
    svc.register_node("n-stale", "Stale Node")
    nodes_map = svc._load_nodes_map()
    nodes_map["n-stale"].last_sync = "2000-01-01T00:00:00+00:00"
    svc._write_nodes(nodes_map)

    result = svc.scan_cluster_health()
    assert result["ok"] is True
    assert "n-stale" in result["stale_node_ids"]
    refreshed = svc._load_nodes_map()["n-stale"]
    assert refreshed.active is False

    from app.tasks.federated_heartbeat_tasks import run_federated_cluster_scan

    monkeypatch.setattr(
        "app.modules.system.services.institution_tier_service.FederatedDeploymentService",
        lambda *args, **kwargs: svc,
    )
    task_result = run_federated_cluster_scan()
    assert task_result["stale_node_ids"] == result["stale_node_ids"]
