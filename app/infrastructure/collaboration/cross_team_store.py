from __future__ import annotations

"""File-backed store for cross-team consensus and anonymous pattern pool."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CrossTeamStore:
    """Persist team consensus votes and site alerts under instance/cross_team/."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        from app.config import BASE_DIR

        self._dir = Path(base_dir or BASE_DIR / "instance" / "cross_team")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._consensus_path = self._dir / "team_consensus.jsonl"
        self._alerts_path = self._dir / "site_alerts.jsonl"
        self._patterns_path = self._dir / "anonymous_patterns.json"
        self._meta_verdicts_path = self._dir / "meta_verdicts.jsonl"

    def append_consensus(self, row: dict[str, Any]) -> None:
        line = json.dumps(row, ensure_ascii=False)
        with self._consensus_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def list_consensus(self, *, limit: int = 500) -> list[dict[str, Any]]:
        return self._read_jsonl(self._consensus_path, limit=limit)

    def append_site_alert(self, row: dict[str, Any]) -> None:
        line = json.dumps(row, ensure_ascii=False)
        with self._alerts_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def list_site_alerts(self, *, limit: int = 80) -> list[dict[str, Any]]:
        rows = self._read_jsonl(self._alerts_path, limit=limit * 3)
        rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return rows[:limit]

    def append_meta_verdict(self, row: dict[str, Any]) -> None:
        line = json.dumps(row, ensure_ascii=False)
        with self._meta_verdicts_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def list_meta_verdicts(self, *, limit: int = 80) -> list[dict[str, Any]]:
        rows = self._read_jsonl(self._meta_verdicts_path, limit=limit * 3)
        rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return rows[:limit]

    def load_patterns(self) -> dict[str, Any]:
        if not self._patterns_path.exists():
            return {"patterns": []}
        try:
            raw = json.loads(self._patterns_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {"patterns": []}
        except Exception as exc:
            logger.warning("cross_team_store.load_patterns: %s", exc)
            return {"patterns": []}

    def save_patterns(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = datetime.utcnow().isoformat()
        self._patterns_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _read_jsonl(path: Path, *, limit: int) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        rows.append(json.loads(raw))
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.warning("cross_team_store._read_jsonl %s: %s", path.name, exc)
        return rows[-limit:]
