from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.domain.topology_schema import SwarmTopologyDescriptor

logger = logging.getLogger(__name__)


class FileSwarmTopologyRepository:
    """Persist user-defined swarm topologies under instance/swarm_topologies/."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        from app.config import BASE_DIR

        self._dir = Path(storage_dir or BASE_DIR / "instance" / "swarm_topologies")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"

    def save(self, user_id: int, topology: SwarmTopologyDescriptor) -> SwarmTopologyDescriptor:
        path = self._dir / f"user_{user_id}_{topology.id}.json"
        path.write_text(
            topology.model_dump_json(indent=2),
            encoding="utf-8",
        )
        self._upsert_index(user_id, topology.id, topology.name)
        return topology

    def get(self, user_id: int, topology_id: str) -> SwarmTopologyDescriptor | None:
        path = self._dir / f"user_{user_id}_{topology_id}.json"
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return SwarmTopologyDescriptor.model_validate(raw)
        except Exception as exc:
            logger.warning("file_swarm_topology_repository.get: %s", exc)
            return None

    def list_for_user(self, user_id: int) -> list[dict[str, Any]]:
        index = self._read_index()
        rows = index.get(str(user_id)) or []
        return list(rows)

    def delete(self, user_id: int, topology_id: str) -> bool:
        path = self._dir / f"user_{user_id}_{topology_id}.json"
        if path.exists():
            path.unlink()
        index = self._read_index()
        uid = str(user_id)
        if uid in index:
            index[uid] = [r for r in index[uid] if r.get("id") != topology_id]
            self._write_index(index)
        return True

    def _upsert_index(self, user_id: int, topology_id: str, name: str) -> None:
        index = self._read_index()
        uid = str(user_id)
        rows = list(index.get(uid) or [])
        rows = [r for r in rows if r.get("id") != topology_id]
        rows.insert(0, {"id": topology_id, "name": name})
        index[uid] = rows[:50]
        self._write_index(index)

    def _read_index(self) -> dict[str, Any]:
        if not self._index_path.exists():
            return {}
        try:
            raw = json.loads(self._index_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except Exception as exc:
            logger.warning("file_swarm_topology_repository._read_index: %s", exc)
            return {}

    def _write_index(self, data: dict[str, Any]) -> None:
        self._index_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
