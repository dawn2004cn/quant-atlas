"""Phase 35 UX-3: strategy deploy snapshot and rollback MVP."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.errors import NotFoundError, ValidationError
from app.modules.strategy.services.strategy.strategy_snapshot_service import StrategySnapshotService
from app.infrastructure.repositories.file_strategy_snapshot_repository import FileStrategySnapshotRepository


@pytest.fixture
def snapshot_service(tmp_path: Path) -> StrategySnapshotService:
    repo = FileStrategySnapshotRepository(tmp_path / "snapshots")
    return StrategySnapshotService(
        repository=repo,
        repo_root=tmp_path,
        freshness_checker=lambda _table, _minutes=15: True,
    )


def test_capture_snapshot_records_metadata(snapshot_service: StrategySnapshotService) -> None:
    snap = snapshot_service.capture_snapshot(
        strategy_name="momentum_v1",
        label="prod deploy",
        strategy_config={"factors": [{"name": "rsi"}]},
        deployed_by="tester",
    )
    assert snap.strategy_name == "momentum_v1"
    assert snap.is_active is True
    assert snap.code_revision.get("vcs") in {"git", "svn", "unknown"}
    assert "runtime_flags" in snap.settings_snapshot
    assert snap.benchmark_meta.get("data_fresh") is True


def test_list_and_get_snapshot(snapshot_service: StrategySnapshotService) -> None:
    created = snapshot_service.capture_snapshot(strategy_name="alpha_a", mark_active=False)
    rows = snapshot_service.list_snapshots(strategy_name="alpha_a")
    assert len(rows) == 1
    loaded = snapshot_service.get_snapshot(created.id)
    assert loaded.id == created.id


def test_rollback_marks_active_and_returns_steps(snapshot_service: StrategySnapshotService) -> None:
    first = snapshot_service.capture_snapshot(strategy_name="dual_ma", label="v1")
    second = snapshot_service.capture_snapshot(strategy_name="dual_ma", label="v2")
    assert second.is_active is True

    result = snapshot_service.rollback(first.id, rolled_back_by="ops")
    assert result.active is True
    assert result.snapshot_id == first.id
    assert len(result.redeploy_steps) >= 2

    active = snapshot_service.get_snapshot(first.id)
    assert active.is_active is True
    inactive = snapshot_service.get_snapshot(second.id)
    assert inactive.is_active is False


def test_get_missing_snapshot_raises(snapshot_service: StrategySnapshotService) -> None:
    with pytest.raises(NotFoundError):
        snapshot_service.get_snapshot("missing-id")


def test_capture_requires_strategy_name(snapshot_service: StrategySnapshotService) -> None:
    with pytest.raises(ValidationError):
        snapshot_service.capture_snapshot(strategy_name="")


def test_rollback_apply_settings_writes_file(snapshot_service: StrategySnapshotService, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    settings_path = config_dir / "settings.json"
    settings_path.write_text('{"old": true}\n', encoding="utf-8")

    snap = snapshot_service.capture_snapshot(
        strategy_name="cfg_test",
        strategy_config={},
    )
    snap.settings_snapshot["config/settings.json"] = {"restored": True, "version": 2}
    snapshot_service._repository.save(snap)

    import app.modules.strategy.services.strategy.strategy_snapshot_service as mod

    original_config_dir = mod.CONFIG_DIR
    mod.CONFIG_DIR = config_dir
    try:
        result = snapshot_service.rollback(snap.id, apply_settings=True)
        assert result.settings_applied is True
        assert result.settings_backup_path
        restored = json.loads(settings_path.read_text(encoding="utf-8"))
        assert restored.get("restored") is True
    finally:
        mod.CONFIG_DIR = original_config_dir
