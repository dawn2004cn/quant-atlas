from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
import logging
logger = logging.getLogger(__name__)



class DecisionEventJournal:
    """Lightweight JSON journal of user decision events.

    Each event records *what* the user did, *when*, and *in what context*.
    Used to surface decision patterns back to the user and (optionally)
    to nudge role presets.
    """

    def __init__(self, *, store_path: Path) -> None:
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(
        self,
        user_id: str | int,
        *,
        event_type: str,
        symbol: str = "",
        market: str = "CN",
        page: str = "",
        component: str = "",
        action: str = "",
        detail: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        uid = str(user_id or "anonymous")
        entry = {
            "event_type": event_type,
            "symbol": str(symbol or "").strip().upper(),
            "market": (market or "CN").upper(),
            "page": page or "",
            "component": component or "",
            "action": action or "",
            "detail": detail or {},
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        with self._lock:
            rows = self._read()
            user_events: list[dict[str, Any]] = rows.get(uid) or []
            user_events.append(entry)
            rows[uid] = user_events
            self._write(rows)
        return entry

    def history(
        self,
        user_id: str | int,
        *,
        limit: int = 50,
        event_type: str | None = None,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        uid = str(user_id or "anonymous")
        with self._lock:
            rows = self._read()
            events: list[dict[str, Any]] = list(rows.get(uid) or [])
        events.reverse()
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        if symbol:
            sym = str(symbol).strip().upper()
            events = [e for e in events if e.get("symbol") == sym]
        return events[: max(1, min(int(limit), 500))]

    def summary(self, user_id: str | int) -> dict[str, Any]:
        uid = str(user_id or "anonymous")
        with self._lock:
            rows = self._read()
            events: list[dict[str, Any]] = list(rows.get(uid) or [])
        total = len(events)
        if total == 0:
            return {"total_events": 0, "recent_actions": [], "frequent_symbols": []}
        recent = events[-10:]
        by_type: dict[str, int] = {}
        symbols: dict[str, int] = {}
        for e in events:
            by_type[e.get("event_type", "unknown")] = by_type.get(e.get("event_type", "unknown"), 0) + 1
            sym = e.get("symbol", "")
            if sym:
                symbols[sym] = symbols.get(sym, 0) + 1
        top_symbols = sorted(symbols.items(), key=lambda x: -x[1])[:5]
        return {
            "total_events": total,
            "by_type": by_type,
            "frequent_symbols": [{"symbol": s, "count": c} for s, c in top_symbols],
            "recent_actions": [
                {
                    "event_type": e.get("event_type"),
                    "symbol": e.get("symbol"),
                    "action": e.get("action"),
                    "timestamp": e.get("timestamp"),
                }
                for e in recent
            ],
        }

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        if not self._store_path.exists():
            return {}
        try:
            raw = json.loads(self._store_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw
        except Exception:
            logger.warning("Suppressed exception", exc_info=True)
            pass
        return {}

    def _write(self, rows: dict[str, list[dict[str, Any]]]) -> None:
        self._store_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


__all__ = ["DecisionEventJournal"]
