from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.domain.dto.decision_snapshot_dto import DecisionResearchSnapshotDTO

logger = logging.getLogger(__name__)


class FileDecisionSnapshotRepository:
    """Persist decision research snapshots under instance/decision_snapshots/."""

    def __init__(self, storage_dir: Path) -> None:
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: DecisionResearchSnapshotDTO) -> DecisionResearchSnapshotDTO:
        path = self._dir / f"{snapshot.id}.json"
        path.write_text(
            snapshot.model_dump(mode="json"),
            encoding="utf-8",
        )
        return snapshot

    def get(self, snapshot_id: str) -> DecisionResearchSnapshotDTO | None:
        path = self._dir / f"{snapshot_id}.json"
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return DecisionResearchSnapshotDTO.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("file_decision_snapshot_repository.get: %s", exc)
            return None

    def get_by_share_token(self, share_token: str) -> DecisionResearchSnapshotDTO | None:
        token = str(share_token or "").strip()
        if not token:
            return None
        for path in self._dir.glob("*.json"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                dto = DecisionResearchSnapshotDTO.model_validate(raw)
                if dto.share_token == token:
                    return dto
            except Exception as exc:  # noqa: BLE001
                logger.debug("get_by_share_token %s: %s", path.name, exc)
        return None

    def list_recent(self, *, limit: int = 50, symbol: str | None = None) -> list[DecisionResearchSnapshotDTO]:
        rows: list[tuple[str, DecisionResearchSnapshotDTO]] = []
        for path in self._dir.glob("*.json"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                dto = DecisionResearchSnapshotDTO.model_validate(raw)
                if symbol and dto.symbol.upper() != symbol.upper():
                    continue
                rows.append((dto.created_at.isoformat() if hasattr(dto.created_at, "isoformat") else str(dto.created_at), dto))
            except Exception as exc:  # noqa: BLE001
                logger.debug("skip snapshot %s: %s", path.name, exc)
        rows.sort(key=lambda x: x[0], reverse=True)
        return [dto for _, dto in rows[: max(1, limit)]]
