from __future__ import annotations

from datetime import datetime

from app.domain.entities import Experiment


def test_experiment_resolved_metrics_prefers_metadata():
    exp = Experiment(
        id="e1",
        name="alpha-1",
        swarm_run_id="sw1",
        preset_name="default",
        status="completed",
        metadata={"metrics": {"sharpe": 1.2}},
        artifacts={"metrics": {"sharpe": 0.5}},
    )
    assert exp.resolved_metrics() == {"sharpe": 1.2}


def test_experiment_resolved_equity_curve_from_artifacts():
    curve = [{"date": "2024-01-01", "value": 1.0}]
    exp = Experiment(
        id="e2",
        name="alpha-2",
        swarm_run_id="sw1",
        preset_name="default",
        status="completed",
        artifacts={"equity_curve": curve},
    )
    assert exp.resolved_equity_curve() == curve


def test_experiment_to_api_detail_includes_preset_name():
    created = datetime(2024, 6, 1, 12, 0, 0)
    exp = Experiment(
        id="e3",
        name="run-3",
        swarm_run_id="sw9",
        preset_name="momentum",
        status="running",
        created_at=created,
        metadata={"description": "test run"},
    )
    payload = exp.to_api_detail()
    assert payload["id"] == "e3"
    assert payload["preset_name"] == "momentum"
    assert payload["description"] == "test run"
    assert payload["created_at"] == created.isoformat()
