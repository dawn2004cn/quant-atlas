"""Config snapshot archive — hash-locked decision reproducibility."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ConfigSnapshot:
    snapshot_id: str
    source: str = ""
    strategy_hash: str = ""
    runtime_hash: str = ""
    config_sha256: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class ConfigSnapshotArchive:
    """Minimal reproducible-config archive (in-memory).

    Records a SHA-256 digest of the active config at decision time.
    """

    def __init__(self) -> None:
        self._items: dict[str, ConfigSnapshot] = {}

    def record(self, snapshot: ConfigSnapshot) -> ConfigSnapshot:
        self._items[snapshot.snapshot_id] = snapshot
        return snapshot

    def get(self, snapshot_id: str) -> ConfigSnapshot | None:
        return self._items.get(snapshot_id)

    def list_recent(self, limit: int = 20) -> list[ConfigSnapshot]:
        items = sorted(self._items.values(), key=lambda s: s.created_at, reverse=True)
        return items[: max(1, limit)]

    @staticmethod
    def sha256_of_dict(cfg: dict[str, Any]) -> str:
        try:
            raw = json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str)
        except Exception:
            raw = str(cfg)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
