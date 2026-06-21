from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StrategyDeploySnapshotDTO(BaseModel):
    """Immutable deploy snapshot: code revision, settings backup, benchmark metadata."""

    id: str
    strategy_name: str
    label: str = ""
    code_revision: dict[str, str] = Field(default_factory=dict)
    deploy_profile: str = "dev"
    settings_snapshot: dict[str, Any] = Field(default_factory=dict)
    benchmark_meta: dict[str, Any] = Field(default_factory=dict)
    strategy_config: dict[str, Any] = Field(default_factory=dict)
    deployed_at: datetime = Field(default_factory=datetime.now)
    deployed_by: str = "system"
    is_active: bool = False
    notes: str = ""


class StrategyRollbackResultDTO(BaseModel):
    """Rollback outcome with redeploy instructions."""

    snapshot_id: str
    strategy_name: str
    active: bool
    code_revision: dict[str, str] = Field(default_factory=dict)
    redeploy_steps: list[str] = Field(default_factory=list)
    settings_to_restore: dict[str, Any] = Field(default_factory=dict)
    settings_applied: bool = False
    settings_backup_path: str | None = None
    code_applied: bool = False
    code_checkout_message: str = ""
    message: str = ""
