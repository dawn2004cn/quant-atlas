from __future__ import annotations

"""Strategy deploy snapshot capture and rollback orchestration."""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from collections.abc import Callable

from app.application.errors import NotFoundError, ValidationError
from app.modules.system.services.helpers.code_checkout import checkout_code_revision, is_code_checkout_allowed
from app.modules.system.services.helpers.code_revision import resolve_code_revision
from app.bootstrap_components.runtime_config_validator import resolve_deploy_profile
from app.config.settings import BASE_DIR, CONFIG_DIR, INSTANCE_DIR
from app.domain.dto.strategy_snapshot_dto import (
    StrategyDeploySnapshotDTO,
    StrategyRollbackResultDTO,
)
from app.domain.ports.strategy_snapshot_port import StrategySnapshotPort
from app.infrastructure.repositories.file_strategy_snapshot_repository import (
    FileStrategySnapshotRepository,
)


class StrategySnapshotService:
    """Capture deploy metadata and provide rollback instructions."""

    def __init__(
        self,
        repository: StrategySnapshotPort | None = None,
        *,
        repo_root: Path | None = None,
        freshness_checker: Callable[[str, int], bool] | None = None,
    ) -> None:
        storage = INSTANCE_DIR / "strategy_snapshots"
        self._repository = repository or FileStrategySnapshotRepository(storage)
        self._repo_root = repo_root or BASE_DIR
        self._freshness_checker = freshness_checker

    def capture_snapshot(
        self,
        *,
        strategy_name: str,
        label: str = "",
        notes: str = "",
        strategy_config: dict[str, Any] | None = None,
        deployed_by: str = "system",
        mark_active: bool = True,
    ) -> StrategyDeploySnapshotDTO:
        name = (strategy_name or "").strip()
        if not name:
            raise ValidationError("strategy_name_required")

        snapshot = StrategyDeploySnapshotDTO(
            id=str(uuid.uuid4()),
            strategy_name=name,
            label=(label or "").strip() or f"{name}@{datetime.now():%Y-%m-%d %H:%M}",
            code_revision=resolve_code_revision(self._repo_root),
            deploy_profile=resolve_deploy_profile(),
            settings_snapshot=self._capture_settings_snapshot(),
            benchmark_meta=self._capture_benchmark_meta(),
            strategy_config=strategy_config or {},
            deployed_at=datetime.now(),
            deployed_by=deployed_by,
            is_active=False,
            notes=notes,
        )
        saved = self._repository.save(snapshot)
        if mark_active:
            activated = self._repository.set_active(saved.id)
            return activated or saved
        return saved

    def list_snapshots(
        self,
        *,
        strategy_name: str | None = None,
        limit: int = 50,
    ) -> list[StrategyDeploySnapshotDTO]:
        return self._repository.list(strategy_name=strategy_name, limit=limit)

    def get_snapshot(self, snapshot_id: str) -> StrategyDeploySnapshotDTO:
        snap = self._repository.get(snapshot_id)
        if snap is None:
            raise NotFoundError("strategy_snapshot_not_found")
        return snap

    def rollback(
        self,
        snapshot_id: str,
        *,
        rolled_back_by: str = "system",
        apply_settings: bool = False,
        apply_code: bool = False,
    ) -> StrategyRollbackResultDTO:
        self.get_snapshot(snapshot_id)
        activated = self._repository.set_active(snapshot_id)
        if activated is None:
            raise NotFoundError("strategy_snapshot_not_found")

        vcs = activated.code_revision.get("vcs", "unknown")
        revision = activated.code_revision.get("revision", "unknown")
        steps = [f"Mark snapshot {activated.id} as active deploy baseline."]

        code_applied = False
        code_checkout_message = ""
        if apply_code:
            if not is_code_checkout_allowed():
                steps.append(
                    "Code checkout blocked: set STRATEGY_SNAPSHOT_ALLOW_CODE_CHECKOUT=1 "
                    "(and STRATEGY_SNAPSHOT_FORCE_CODE_CHECKOUT=1 in prod)."
                )
                code_checkout_message = "code_checkout_not_allowed"
            else:
                code_applied, code_checkout_message = checkout_code_revision(
                    self._repo_root,
                    activated.code_revision,
                )
                if code_applied:
                    steps.append(
                        f"Checked out {activated.code_revision.get('vcs')} revision {code_checkout_message}."
                    )
                else:
                    steps.append(f"Code checkout failed: {code_checkout_message}")
        elif vcs == "git" and revision != "unknown":
            steps.append(f"git checkout {revision}")
        elif vcs == "svn" and revision != "unknown":
            steps.append(f"svn update -r {revision}")
        else:
            steps.append("Manually restore code to the revision recorded in snapshot metadata.")

        settings_applied = False
        settings_backup_path: str | None = None
        settings_file = activated.settings_snapshot.get("config/settings.json")
        if apply_settings and settings_file is not None:
            settings_applied, settings_backup_path = self._restore_settings_from_snapshot(
                activated.settings_snapshot
            )
            if settings_applied:
                steps.append(
                    f"Restored config/settings.json automatically (backup: {settings_backup_path})."
                )
            else:
                steps.append("Failed to auto-restore config/settings.json; restore manually from snapshot.")
        elif settings_file is not None:
            steps.append("Restore config/settings.json from snapshot.settings_snapshot.")
        steps.append("Redeploy strategy pipeline / restart workers if configs changed.")

        message = f"Rollback recorded by {rolled_back_by}"
        if apply_code and code_applied:
            message += "; code revision checked out"
        elif apply_code:
            message += f"; code checkout failed ({code_checkout_message})"
        if apply_settings and settings_applied:
            message += "; settings.json restored"
        elif apply_settings:
            message += "; settings restore skipped or failed"
        if not apply_code and not apply_settings:
            message += "; follow redeploy_steps for full restore"

        return StrategyRollbackResultDTO(
            snapshot_id=activated.id,
            strategy_name=activated.strategy_name,
            active=True,
            code_revision=activated.code_revision,
            redeploy_steps=steps,
            settings_to_restore=activated.settings_snapshot,
            settings_applied=settings_applied,
            settings_backup_path=settings_backup_path,
            code_applied=code_applied,
            code_checkout_message=code_checkout_message,
            message=message,
        )

    def _restore_settings_from_snapshot(self, settings_snapshot: dict[str, Any]) -> tuple[bool, str | None]:
        raw = settings_snapshot.get("config/settings.json")
        if not isinstance(raw, dict) or raw.get("_error"):
            return False, None
        settings_path = CONFIG_DIR / "settings.json"
        backup_path = CONFIG_DIR / f"settings.json.bak.{datetime.now():%Y%m%d%H%M%S}"
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            if settings_path.is_file():
                shutil.copy2(settings_path, backup_path)
            settings_path.write_text(
                json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return True, str(backup_path)
        except OSError:
            return False, None

    def _capture_settings_snapshot(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"runtime_flags": self._safe_runtime_flags()}
        settings_path = CONFIG_DIR / "settings.json"
        if settings_path.is_file():
            try:
                payload["config/settings.json"] = json.loads(settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload["config/settings.json"] = {"_error": "invalid_json"}
        payload["deploy_profile"] = resolve_deploy_profile()
        return payload

    def _safe_runtime_flags(self) -> dict[str, Any]:
        try:
            from app.config import get_settings

            settings = get_settings()
            return {
                "database_backend": settings.database_backend,
                "enable_qlib": settings.enable_qlib,
                "enable_rd_agent": settings.enable_rd_agent,
                "enable_celery": settings.enable_celery,
                "enable_background_scanner": settings.enable_background_scanner,
            }
        except Exception:
            return {}

    def _capture_benchmark_meta(self) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "benchmark_symbol": "000001.SH",
            "history_table": "stock_history_sh",
            "checked_at": datetime.now().isoformat(),
        }
        if self._freshness_checker is None:
            meta["data_fresh"] = None
            meta["note"] = "freshness_checker_not_bound"
            return meta
        try:
            meta["data_fresh"] = self._freshness_checker("stock_history_sh", 15)
        except Exception as exc:
            meta["data_fresh"] = None
            meta["error"] = str(exc)[:200]
        return meta
