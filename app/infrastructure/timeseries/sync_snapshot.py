from __future__ import annotations

"""Persist last QuestDB/ClickHouse OHLCV sync summary for health probes."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import INSTANCE_DIR
from app.core.logger import get_logger

logger = get_logger(__name__)

_SNAPSHOT_PATH = INSTANCE_DIR / "timeseries_sync_snapshot.json"
_PROGRESS_PATH = INSTANCE_DIR / "timeseries_sync_progress.json"
_HISTORY_PATH = INSTANCE_DIR / "timeseries_sync_history.jsonl"
_HISTORY_MAX_LINES = 365
_REDIS_PROGRESS_KEY = "quant:timeseries_sync_progress"
_REDIS_PROGRESS_TTL_SEC = 7200


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _redis_client() -> Any | None:
    try:
        from app.core.runtime_config import get_runtime
        from app.infrastructure.redis_client import RedisClientPool

        url = (get_runtime("REDIS_URL", "") or "").strip()
        if not url:
            return None
        return RedisClientPool.get(url).client
    except Exception as exc:
        logger.debug("timeseries sync progress redis unavailable: %s", exc)
        return None


def set_timeseries_sync_progress(
    *,
    status: str,
    symbols_total: int = 0,
    symbols_done: int = 0,
    source: str = "sync",
    message: str = "",
) -> None:
    """Publish in-flight sync progress (file + optional Redis)."""
    payload: dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "symbols_total": int(symbols_total),
        "symbols_done": int(symbols_done),
        "source": source,
        "message": message,
    }
    if symbols_total > 0:
        payload["percent"] = min(100, int(symbols_done * 100 / symbols_total))
    try:
        INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
        _write_json(_PROGRESS_PATH, payload)
    except OSError as exc:
        logger.warning("set_timeseries_sync_progress file failed: %s", exc)
    client = _redis_client()
    if client is not None:
        try:
            client.setex(
                _REDIS_PROGRESS_KEY,
                _REDIS_PROGRESS_TTL_SEC,
                json.dumps(payload, ensure_ascii=False),
            )
        except Exception as exc:
            logger.debug("set_timeseries_sync_progress redis failed: %s", exc)


def get_timeseries_sync_progress() -> dict[str, Any] | None:
    client = _redis_client()
    if client is not None:
        try:
            raw = client.get(_REDIS_PROGRESS_KEY)
            if raw:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
        except Exception as exc:
            logger.debug("get_timeseries_sync_progress redis: %s", exc)
    if not _PROGRESS_PATH.is_file():
        return None
    try:
        data = json.loads(_PROGRESS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("get_timeseries_sync_progress file: %s", exc)
        return None


def _append_sync_history(payload: dict[str, Any]) -> None:
    """Append-only JSONL ring buffer for ops dashboards (no secrets)."""
    try:
        INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_HISTORY_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        _trim_sync_history(_HISTORY_MAX_LINES)
    except OSError as exc:
        logger.warning("append_sync_history failed: %s", exc)


def _trim_sync_history(max_lines: int) -> None:
    if not _HISTORY_PATH.is_file():
        return
    try:
        lines = _HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        if len(lines) <= max_lines:
            return
        _HISTORY_PATH.write_text(
            "\n".join(lines[-max_lines:]) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.debug("trim_sync_history: %s", exc)


def get_timeseries_sync_history(
    *,
    limit: int = 20,
    source: str | None = None,
) -> list[dict[str, Any]]:
    """Return recent sync runs newest-first (capped at 100)."""
    cap = max(1, min(int(limit), 100))
    if not _HISTORY_PATH.is_file():
        return []
    try:
        lines = _HISTORY_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.debug("get_timeseries_sync_history: %s", exc)
        return []
    rows: list[dict[str, Any]] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if source and row.get("source") != source:
            continue
        rows.append(row)
        if len(rows) >= cap:
            break
    return rows


def clear_timeseries_sync_progress() -> None:
    try:
        if _PROGRESS_PATH.is_file():
            _PROGRESS_PATH.unlink()
    except OSError as exc:
        logger.debug("clear_timeseries_sync_progress file: %s", exc)
    client = _redis_client()
    if client is not None:
        try:
            client.delete(_REDIS_PROGRESS_KEY)
        except Exception as exc:
            logger.debug("clear_timeseries_sync_progress redis: %s", exc)


def record_timeseries_sync_snapshot(result: dict[str, Any], *, source: str = "sync") -> None:
    """Write a compact summary of the latest sync run (file-backed, no secrets)."""
    q = result.get("questdb") if isinstance(result.get("questdb"), dict) else {}
    ch = result.get("clickhouse") if isinstance(result.get("clickhouse"), dict) else {}
    payload: dict[str, Any] = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "ok": bool(result.get("ok")),
        "skipped": bool(result.get("skipped")),
        "reason": result.get("reason") or result.get("error"),
        "mode": result.get("mode"),
        "symbols_requested": result.get("symbols_requested"),
        "up_to_date": result.get("up_to_date"),
        "questdb_rows_written": int(q.get("rows_written") or 0),
        "clickhouse_rows_written": int(ch.get("rows_written") or 0),
        "failed_samples": len(result.get("failed_samples") or []),
    }
    try:
        INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
        _write_json(_SNAPSHOT_PATH, payload)
        _append_sync_history(payload)
    except OSError as exc:
        logger.warning("record_timeseries_sync_snapshot failed: %s", exc)


def get_timeseries_sync_snapshot() -> dict[str, Any] | None:
    if not _SNAPSHOT_PATH.is_file():
        return None
    try:
        data = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("get_timeseries_sync_snapshot: %s", exc)
        return None


def describe_questdb_sync_beat() -> dict[str, Any]:
    """QuestDB/ClickHouse Celery Beat retired (history ingest = Timescale/CSV/Qlib)."""
    from app.core.runtime_config import get_runtime_int

    out: dict[str, Any] = {
        "enabled": False,
        "retired": True,
        "reason": "questdb_clickhouse_ingest_retired",
        "preferred": ["timescale", "csv", "qlib"],
        "celery_beat_key": "questdb-ohlcv-after-close",
        "task": "app.tasks.questdb_sync_tasks.questdb_ohlcv_sync_tick",
        "schedule_hour": 16,
        "schedule_minute": 35,
        "schedule_label": "retired",
        "sync_limit": get_runtime_int("TIMESERIES_SYNC_LIMIT", 0),
        "max_symbols_cap": get_runtime_int("TIMESERIES_SYNC_MAX_SYMBOLS", 50_000),
    }
    snap = get_timeseries_sync_snapshot()
    if snap:
        out["last_sync"] = {
            "recorded_at": snap.get("recorded_at"),
            "source": snap.get("source"),
            "ok": snap.get("ok"),
            "mode": snap.get("mode"),
        }
    return out


def describe_timeseries_backfill_status() -> dict[str, Any]:
    """Ops summary: row count vs backfill target and TDX universe coverage."""
    from app.core.runtime_config import get_runtime_int
    from app.infrastructure.timeseries.ohlcv_history_reader import probe_ohlcv_tables

    target_rows = get_runtime_int("TIMESERIES_BACKFILL_TARGET_ROWS", 1_000_000)
    ohlcv = probe_ohlcv_tables()
    rows = int(ohlcv.get("questdb_rows") or 0)
    universe = 0
    try:
        from app.modules.data.services.tdx_code_cache import get_tdx_cn_universe

        universe = len(get_tdx_cn_universe())
    except Exception as exc:
        logger.debug("describe_timeseries_backfill_status universe: %s", exc)

    coverage_pct = round(min(100.0, rows / target_rows * 100.0), 2) if target_rows > 0 else 0.0
    snap = get_timeseries_sync_snapshot()
    progress = get_timeseries_sync_progress()
    last_backfill = None
    if snap and str(snap.get("source") or "") in ("backfill", "sync"):
        last_backfill = snap

    return {
        "target_rows": target_rows,
        "questdb_rows": rows,
        "coverage_pct": coverage_pct,
        "meets_target": rows >= target_rows,
        "recommended": rows < target_rows,
        "universe_symbols": universe,
        "sync_in_progress": bool(progress and progress.get("status") == "running"),
        "sync_progress": progress,
        "last_backfill": last_backfill,
        "ohlcv_tables": ohlcv,
    }
