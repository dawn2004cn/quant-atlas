from __future__ import annotations

"""Strategy snapshot facade over ``StrategySnapshotService``."""

from typing import Any

from app.modules.strategy.services.strategy.strategy_snapshot_service import StrategySnapshotService
from app.domain.dto.strategy_snapshot_dto import (
    StrategyDeploySnapshotDTO,
    StrategyRollbackResultDTO,
)


class SnapshotsFacade:
    """Thin SDK wrapper for deploy snapshots and rollback."""

    def __init__(self, service: StrategySnapshotService | None = None) -> None:
        self._service = service or StrategySnapshotService()

    def capture(
        self,
        *,
        strategy_name: str,
        label: str = "",
        notes: str = "",
        strategy_config: dict[str, Any] | None = None,
        deployed_by: str = "sdk",
        mark_active: bool = True,
    ) -> StrategyDeploySnapshotDTO:
        return self._service.capture_snapshot(
            strategy_name=strategy_name,
            label=label,
            notes=notes,
            strategy_config=strategy_config,
            deployed_by=deployed_by,
            mark_active=mark_active,
        )

    def list(
        self,
        *,
        strategy_name: str | None = None,
        limit: int = 50,
    ) -> list[StrategyDeploySnapshotDTO]:
        return self._service.list_snapshots(strategy_name=strategy_name, limit=limit)

    def get(self, snapshot_id: str) -> StrategyDeploySnapshotDTO:
        return self._service.get_snapshot(snapshot_id)

    def rollback(self, snapshot_id: str, *, rolled_back_by: str = "sdk", apply_settings: bool = False, apply_code: bool = False) -> StrategyRollbackResultDTO:
        return self._service.rollback(
            snapshot_id,
            rolled_back_by=rolled_back_by,
            apply_settings=apply_settings,
            apply_code=apply_code,
        )

    def capture_dict(self, **kwargs: Any) -> dict[str, Any]:
        return self.capture(**kwargs).model_dump(mode="json")
