from __future__ import annotations

"""Persist last alert dispatch fingerprint to avoid notification spam."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from app.config.settings import INSTANCE_DIR

logger = logging.getLogger(__name__)


class AlertDispatchStateStore:
    """Track last successful dispatch fingerprint and timestamp."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (INSTANCE_DIR / "alert_dispatch_state.json")

    def should_skip(self, fingerprint: str, *, cooldown_minutes: int) -> bool:
        if cooldown_minutes <= 0 or not fingerprint:
            return False
        state = self._read()
        if state.get("fingerprint") != fingerprint:
            return False
        ts_raw = state.get("dispatched_at")
        if not ts_raw:
            return False
        try:
            last = datetime.fromisoformat(str(ts_raw))
        except ValueError:
            return False
        return datetime.now() - last < timedelta(minutes=cooldown_minutes)

    def record(self, fingerprint: str) -> None:
        if not fingerprint:
            return
        payload = {"fingerprint": fingerprint, "dispatched_at": datetime.now().isoformat()}
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("alert_dispatch_state_store.record failed: %s", exc)

    def _read(self) -> dict:
        if not self._path.is_file():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
