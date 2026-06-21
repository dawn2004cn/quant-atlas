from __future__ import annotations

"""JSON file repository for strategy deploy snapshots."""

import json
import logging
from datetime import datetime
from pathlib import Path

from app.domain.dto.strategy_snapshot_dto import StrategyDeploySnapshotDTO

logger = logging.getLogger(__name__)


class FileStrategySnapshotRepository:
    """Persist snapshots under ``instance/strategy_snapshots/*.json``."""

    def __init__(self, storage_dir: Path) -> None:
        self._root = Path(storage_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, snapshot_id: str) -> Path:
        return self._root / f"{snapshot_id}.json"

    def save(self, snapshot: StrategyDeploySnapshotDTO) -> StrategyDeploySnapshotDTO:
        path = self._path(snapshot.id)
        path.write_text(
            json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return snapshot

    def get(self, snapshot_id: str) -> StrategyDeploySnapshotDTO | None:
        path = self._path(snapshot_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return StrategyDeploySnapshotDTO.model_validate(data)
        except Exception as exc:
            logger.warning("file_strategy_snapshot_repository.get: %s", exc)
            return None

    def list(
        self,
        *,
        strategy_name: str | None = None,
        limit: int = 50,
    ) -> list[StrategyDeploySnapshotDTO]:
        rows: list[StrategyDeploySnapshotDTO] = []
        for path in sorted(self._root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.name.startswith("_"):
                continue
            snap = self.get(path.stem)
            if snap is None:
                continue
            if strategy_name and snap.strategy_name != strategy_name:
                continue
            rows.append(snap)
            if len(rows) >= max(1, min(limit, 200)):
                break
        return rows

    def set_active(self, snapshot_id: str) -> StrategyDeploySnapshotDTO | None:
        target = self.get(snapshot_id)
        if target is None:
            return None
        for path in self._root.glob("*.json"):
            if path.name.startswith("_"):
                continue
            snap = self.get(path.stem)
            if snap is None or snap.strategy_name != target.strategy_name:
                continue
            updated = snap.model_copy(update={"is_active": snap.id == snapshot_id})
            self.save(updated)
        return self.get(snapshot_id)
