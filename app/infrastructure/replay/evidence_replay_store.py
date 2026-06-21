from __future__ import annotations
"""Append-only evidence replay snapshots per symbol."""

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import BASE_DIR

_lock = threading.Lock()
_STORE_DIR = BASE_DIR / "instance" / "evidence_replay"


def _path(symbol: str, market: str) -> Path:
    key = f"{(market or 'CN').upper()}_{(symbol or '').strip().upper()}"
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    return _STORE_DIR / f"{key}.jsonl"


def append_snapshot(
    symbol: str,
    market: str,
    *,
    event_type: str,
    payload: dict[str, Any],
    source: str = "",
) -> None:
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event_type": event_type,
        "source": source,
        "symbol": symbol.upper(),
        "market": market.upper(),
        "payload": payload,
    }
    path = _path(symbol, market)
    with _lock:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def list_snapshots(
    symbol: str,
    market: str = "CN",
    *,
    minutes_back: int = 120,
    limit: int = 100,
) -> list[dict[str, Any]]:
    path = _path(symbol, market)
    if not path.is_file():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max(1, minutes_back))
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in reversed(lines):
        if len(rows) >= limit:
            break
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = row.get("timestamp")
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.now(timezone.utc)
        if dt >= cutoff:
            rows.append(row)
    rows.reverse()
    return rows
