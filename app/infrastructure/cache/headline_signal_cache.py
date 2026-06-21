from __future__ import annotations

"""File-backed cache for offline headline signal annotations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config.settings import INSTANCE_DIR

logger = logging.getLogger(__name__)


class HeadlineSignalCache:
    """Persist Celery batch headline signal tags under ``instance/headline_signals/``."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or (INSTANCE_DIR / "headline_signals")

    def load(self, market: str) -> dict[str, dict[str, Any]]:
        path = self._path(market)
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("headline_signal_cache.load failed (%s): %s", path, exc)
            return {}
        entries = data.get("entries") if isinstance(data, dict) else None
        return entries if isinstance(entries, dict) else {}

    def save(self, market: str, entries: dict[str, dict[str, Any]]) -> None:
        path = self._path(market)
        payload = {
            "market": market.upper(),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entries": entries,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("headline_signal_cache.save failed (%s): %s", path, exc)

    def merge(self, market: str, patch: dict[str, dict[str, Any]]) -> None:
        if not patch:
            return
        current = self.load(market)
        current.update(patch)
        self.save(market, current)

    def _path(self, market: str) -> Path:
        safe = "".join(ch for ch in str(market or "CN").upper() if ch.isalnum()) or "CN"
        return self._root / f"{safe}.json"
