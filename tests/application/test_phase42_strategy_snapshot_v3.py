"""Phase 42 UX-3 v3: deploy hook + controlled code checkout."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.modules.system.services.helpers.code_checkout import checkout_code_revision, is_code_checkout_allowed
from app.modules.strategy.services.strategy.strategy_snapshot_hook import capture_on_deploy
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


def test_code_checkout_blocked_without_env() -> None:
    with patch("app.modules.system.services.helpers.code_checkout.get_runtime_bool", return_value=False):
        assert is_code_checkout_allowed() is False


def test_code_checkout_blocked_in_prod_without_force() -> None:
    with patch("app.modules.system.services.helpers.code_checkout.get_runtime_bool") as mock_bool, patch(
        "app.modules.system.services.helpers.code_checkout.resolve_deploy_profile",
        return_value="prod",
    ):
        mock_bool.side_effect = lambda key, default=False: key == "STRATEGY_SNAPSHOT_ALLOW_CODE_CHECKOUT"
        assert is_code_checkout_allowed() is False


def test_checkout_code_revision_runs_git_when_allowed(tmp_path: Path) -> None:
    with patch("app.modules.system.services.helpers.code_checkout.is_code_checkout_allowed", return_value=True), patch(
        "app.modules.system.services.helpers.code_checkout.subprocess.run"
    ) as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "ok"
        ok, msg = checkout_code_revision(tmp_path, {"vcs": "git", "revision": "abc123"})
        assert ok is True
        assert msg == "abc123"
        assert mock_run.call_args.args[0][0] == "git"


def test_rollback_apply_code_when_allowed(snapshot_service: StrategySnapshotService, tmp_path: Path) -> None:
    snap = snapshot_service.capture_snapshot(strategy_name="alpha")
    with patch("app.modules.strategy.services.strategy.strategy_snapshot_service.is_code_checkout_allowed", return_value=True), patch(
        "app.modules.strategy.services.strategy.strategy_snapshot_service.checkout_code_revision",
        return_value=(True, "abc123"),
    ):
        result = snapshot_service.rollback(snap.id, apply_code=True)
    assert result.code_applied is True


def test_capture_on_deploy_respects_disable_flag() -> None:
    with patch("app.modules.strategy.services.strategy.strategy_snapshot_hook.get_runtime_bool", return_value=False):
        assert capture_on_deploy(strategy_name="x") is None


def test_capture_on_deploy_returns_snapshot_meta(tmp_path: Path) -> None:
    with patch("app.modules.strategy.services.strategy.strategy_snapshot_hook.get_runtime_bool", return_value=True), patch(
        "app.modules.strategy.services.strategy.strategy_snapshot_hook.StrategySnapshotService"
    ) as mock_cls:
        mock_cls.return_value.capture_snapshot.return_value = type(
            "S",
            (),
            {"id": "sid-1", "strategy_name": "investment_managers", "label": "batch"},
        )()
        out = capture_on_deploy(strategy_name="investment_managers", label="batch")
        assert out == {"snapshot_id": "sid-1", "strategy_name": "investment_managers", "label": "batch"}
