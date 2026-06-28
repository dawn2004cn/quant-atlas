from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileMetaLearningRepository:
    """Persist meta-learning patterns and evolution run state under instance/meta_learning/."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self._dir = Path(storage_dir or "instance/meta_learning")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._patterns_path = self._dir / "patterns.json"
        self._state_path = self._dir / "state.json"

    def load_patterns(self) -> list[dict[str, Any]]:
        if not self._patterns_path.exists():
            return []
        try:
            raw = json.loads(self._patterns_path.read_text(encoding="utf-8"))
            items = raw.get("patterns") if isinstance(raw, dict) else raw
            return list(items) if isinstance(items, list) else []
        except Exception as exc:
            logger.warning("file_meta_learning_repository.load_patterns: %s", exc)
            return []

    def save_patterns(self, patterns: list[dict[str, Any]]) -> None:
        payload = {"patterns": patterns, "updated_at": datetime.now().isoformat()}
        self._patterns_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_state(self) -> dict[str, Any]:
        if not self._state_path.exists():
            return {}
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except Exception as exc:
            logger.warning("file_meta_learning_repository.load_state: %s", exc)
            return {}

    def save_state(self, state: dict[str, Any]) -> None:
        merged = {**self.load_state(), **state, "updated_at": datetime.now().isoformat()}
        self._state_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
