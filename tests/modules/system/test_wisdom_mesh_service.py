"""WisdomMeshService JSONL store."""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.system.services.mesh.wisdom_mesh_service import WisdomMeshService


def test_upload_list_get_roundtrip(tmp_path: Path) -> None:
    store = tmp_path / "mesh.jsonl"
    svc = WisdomMeshService(store_path=store)
    uploaded = svc.upload_deidentified_strategy(
        user_id="42",
        strategy_spec={"name": "demo", "capital_per_trade": 0.1},
        performance_summary={"sharpe": 1.2},
    )
    listed = svc.list_shared_strategies(limit=5)
    assert len(listed) == 1
    assert listed[0]["id"] == uploaded.id
    got = svc.get_shared_strategy(uploaded.id)
    assert got is not None
    assert got["strategy_name"] == "demo"


def test_vote_and_leaderboard(tmp_path: Path) -> None:
    store = tmp_path / "mesh.jsonl"
    svc = WisdomMeshService(store_path=store)
    strategy = svc.upload_deidentified_strategy(
        user_id="1",
        strategy_spec={"name": "x"},
    )
    contrib = svc.vote_on_factor(
        voter_id="voter-a",
        strategy_id=strategy.id,
        factor_name="momentum",
        proposed_weight=0.5,
        rationale="test",
    )
    assert contrib.votes_for == 1
    lb = svc.get_leaderboard(period="weekly")
    assert lb and lb[0]["score"] >= 1


def test_reload_from_disk(tmp_path: Path) -> None:
    store = tmp_path / "mesh.jsonl"
    svc = WisdomMeshService(store_path=store)
    strategy = svc.upload_deidentified_strategy(user_id="9", strategy_spec={"name": "persist"})
    reloaded = WisdomMeshService(store_path=store)
    assert reloaded.get_shared_strategy(strategy.id) is not None
