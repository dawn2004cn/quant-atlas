from __future__ import annotations

"""Strategy deploy snapshot persistence port."""

from typing import Protocol

from app.domain.dto.strategy_snapshot_dto import StrategyDeploySnapshotDTO


class StrategySnapshotPort(Protocol):
    """Store and query strategy deploy snapshots."""

    def save(self, snapshot: StrategyDeploySnapshotDTO) -> StrategyDeploySnapshotDTO:
        ...

    def get(self, snapshot_id: str) -> StrategyDeploySnapshotDTO | None:
        ...

    def list(
        self,
        *,
        strategy_name: str | None = None,
        limit: int = 50,
    ) -> list[StrategyDeploySnapshotDTO]:
        ...

    def set_active(self, snapshot_id: str) -> StrategyDeploySnapshotDTO | None:
        ...
