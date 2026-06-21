"""Psychology Operation Store — in-memory record of user trading actions.

Tracks add/remove/adopt/sell actions with price context for
psychology guardian analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OperationRecord:
    user_id: int
    action: str  # add, remove, buy, sell, adopt
    symbol: str
    change_pct: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PsychologyOperationStore:
    """In-memory store with optional JSONL persistence."""

    def __init__(self, store_path: str | Path | None = None):
        self._records: dict[int, list[OperationRecord]] = {}
        self._store_path = Path(store_path) if store_path else Path(__file__).resolve().parents[3] / "instance" / "psychology_ops.jsonl"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, user_id: int, action: str, symbol: str, change_pct: float = 0.0) -> OperationRecord:
        rec = OperationRecord(
            user_id=user_id, action=action, symbol=symbol, change_pct=change_pct,
        )
        self._records.setdefault(user_id, []).append(rec)
        self._persist(rec)
        return rec

    def list_recent(self, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
        recs = self._records.get(user_id, [])[-limit:]
        return [
            {
                "action": r.action,
                "symbol": r.symbol,
                "change_pct": r.change_pct,
                "timestamp": r.timestamp,
            }
            for r in recs
        ]

    def clear(self, user_id: int | None = None) -> None:
        if user_id is not None:
            self._records.pop(user_id, None)
        else:
            self._records.clear()

    def _persist(self, rec: OperationRecord) -> None:
        try:
            with self._store_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{rec.user_id},{rec.action},{rec.symbol},{rec.change_pct},{rec.timestamp}\n")
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass


_store: PsychologyOperationStore | None = None


def get_psychology_operation_store() -> PsychologyOperationStore:
    global _store
    if _store is None:
        _store = PsychologyOperationStore()
    return _store
