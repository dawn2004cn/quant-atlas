"""Celery: offline strategy tournament (non-trading hours)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.modules.strategy.services.tournament.offline_runner import run_tournament_batch

logger = get_logger(__name__)


def _nl_strategies_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "instance" / "nl_strategies.jsonl"


def _tournament_runs_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "instance" / "tournament_runs"


def _load_nl_records(limit: int = 200) -> list[dict[str, Any]]:
    path = _nl_strategies_path()
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                rows.append(data)
    # Prefer newest first
    rows.reverse()
    return rows[: max(1, limit)]


def _write_audit(result: dict[str, Any]) -> str | None:
    """Persist a tournament run for ops audit (latest + timestamped)."""
    try:
        out_dir = _tournament_runs_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = {
            "ts": ts,
            **result,
        }
        stamped = out_dir / f"{ts}.json"
        latest = out_dir / "latest.json"
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        stamped.write_text(text, encoding="utf-8")
        latest.write_text(text, encoding="utf-8")
        return str(stamped)
    except Exception:
        logger.warning("tournament audit write failed", exc_info=True)
        return None


def run_strategy_tournament_tick(*, limit: int = 200) -> dict[str, Any]:
    """Load NL candidates and run hard-gate tournament → paper pool."""
    records = _load_nl_records(limit=limit)
    result = run_tournament_batch(records)
    result["source"] = str(_nl_strategies_path())
    result["loaded"] = len(records)
    audit_path = _write_audit(result)
    if audit_path:
        result["audit_path"] = audit_path
    return result


try:
    from app.celery_app import celery
except Exception:  # pragma: no cover
    celery = None  # type: ignore

if celery is not None:

    @celery.task(name="app.tasks.strategy_tournament_tasks.strategy_tournament_tick")
    def strategy_tournament_tick(limit: int = 200) -> dict[str, Any]:
        return run_strategy_tournament_tick(limit=limit)
