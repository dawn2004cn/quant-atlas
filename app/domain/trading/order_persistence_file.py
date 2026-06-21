"""File-backed order persistence (JSON state + JSONL events)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class FileOrderPersistenceBackend:
    """Persist order state and events on local filesystem."""

    def __init__(self, state_file: Path, events_file: Path) -> None:
        self._state_file = state_file
        self._events_file = events_file

    def save_state(self, state: dict[str, Any]) -> bool:
        try:
            temp_file = self._state_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2, default=str)
            temp_file.replace(self._state_file)
            return True
        except Exception as exc:
            logger.error("File save failed: %s", exc)
            return False

    def load_state(self) -> dict[str, Any]:
        if not self._state_file.exists():
            return {}
        with open(self._state_file, encoding="utf-8") as handle:
            return json.load(handle)

    def append_event(self, event: dict[str, Any]) -> bool:
        try:
            with open(self._events_file, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            return True
        except Exception as exc:
            logger.error("Event append failed: %s", exc)
            return False

    def load_events(self, order_id: str | None = None) -> list[dict[str, Any]]:
        if not self._events_file.exists():
            return []
        events: list[dict[str, Any]] = []
        with open(self._events_file, encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if order_id is None or event.get("order_id") == order_id:
                    events.append(event)
        return events
