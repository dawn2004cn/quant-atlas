from __future__ import annotations
"""TDX → TimescaleDB only (split from legacy TDX dayk MySQL/CSV/qlib pipeline)."""

import json
import time
from pathlib import Path
from typing import Any

from app.modules.data.services.tdx_dayk_sync_service import TdxDaykSyncService
from app.config import INSTANCE_DIR, get_settings
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int

logger = get_logger(__name__)

_BACKFILL_STATE = INSTANCE_DIR / "timescale_backfill_state.json"


def _build_tdx_sync_service() -> TdxDaykSyncService:
    from app.infrastructure.repositories.deps import create_tdx_dayk_sync_service

    return create_tdx_dayk_sync_service(require_qlib=False)


def _load_backfill_state() -> dict[str, Any]:
    if not _BACKFILL_STATE.is_file():
        return {}
    try:
        return json.loads(_BACKFILL_STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_backfill_state(payload: dict[str, Any]) -> None:
    _BACKFILL_STATE.parent.mkdir(parents=True, exist_ok=True)
    _BACKFILL_STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_tdx_timescale_sync(
    *,
    limit: int | None = None,
    offset: int = 0,
    mode: str = "full",
    dump_max_workers: int | None = None,
    start_date: str | None = None,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    """Write TDX lday → Timescale ``market_bars`` (+ factors / matviews). No MySQL."""
    from app.modules.data.services.tdx_ohlcv_reader import ensure_tdx_local_file_port
    from app.modules.system.services.helpers.timescale_bar_access import ensure_timescale_bar_port

    ensure_tdx_local_file_port()
    ensure_timescale_bar_port()

    if not get_runtime_bool("ENABLE_TIMESCALE_TDX_SYNC", True):
        return {"ok": True, "skipped": True, "reason": "ENABLE_TIMESCALE_TDX_SYNC=0"}
    settings = get_settings()
    if not settings.use_timescaledb:
        return {"ok": False, "error": "USE_TIMESCALEDB=0"}

    svc = _build_tdx_sync_service()
    workers = dump_max_workers or get_runtime_int("TIMESCALE_SYNC_WORKERS", 4)

    if symbols:
        out = svc.timescale_sync_codes_from_tdx_dayk(
            symbols=symbols,
            dump_max_workers=workers,
        )
    elif mode == "incremental":
        out = svc.incremental_sync_from_tdx_dayk(
            start_date=start_date,
            limit=limit,
            dump_qlib_bin=False,
            dump_max_workers=workers,
            enable_timescale=True,
            enable_csv=False,
            enable_mysql=False,
        )
    else:
        out = svc.timescale_full_sync_from_tdx_dayk(
            limit=limit,
            offset=offset,
            dump_max_workers=workers,
        )
    return dict(out) if isinstance(out, dict) else out.model_dump()


def run_tdx_timescale_backfill(
    *,
    batch_size: int | None = None,
    max_batches: int | None = None,
    offset: int | None = None,
    dump_max_workers: int | None = None,
    resume: bool = True,
) -> dict[str, Any]:
    """Paginated full Timescale backfill from TDX with offset checkpoint."""
    batch = batch_size or get_runtime_int("TIMESCALE_BACKFILL_BATCH", 200)
    batches = max_batches or get_runtime_int("TIMESCALE_BACKFILL_MAX_BATCHES", 0)
    workers = dump_max_workers or get_runtime_int("TIMESCALE_SYNC_WORKERS", 1)
    workers = max(1, min(workers, get_runtime_int("TIMESCALE_MAX_WORKERS", 2)))

    state = _load_backfill_state() if resume else {}
    start_offset = offset if offset is not None else int(state.get("next_offset") or 0)
    aggregated: dict[str, Any] = {
        "ok": True,
        "batches": [],
        "next_offset": start_offset,
        "workers": workers,
        "resumed_from": start_offset if resume and state else None,
    }
    offset = start_offset
    batch_idx = 0
    pause_ratio = float(get_runtime_int("TIMESCALE_BACKFILL_PAUSE_FAIL_PCT", 30)) / 100.0

    while True:
        if batches > 0 and batch_idx >= batches:
            break
        chunk = run_tdx_timescale_sync(
            limit=batch,
            offset=offset,
            mode="full",
            dump_max_workers=workers,
        )
        aggregated["batches"].append({"offset": offset, **chunk})
        stats = chunk.get("stats") or {}
        ts_rows = int(stats.get("timescale_rows") or 0)
        codes_ok = int(stats.get("codes_ok") or 0)
        codes_failed = int(stats.get("codes_failed") or 0)
        codes_total = int(stats.get("codes_total") or 0)
        if chunk.get("ok") and (ts_rows > 0 or codes_ok > 0):
            aggregated["ok"] = True
        if codes_total and codes_failed / codes_total >= pause_ratio:
            aggregated["ok"] = False
            aggregated["paused"] = True
            aggregated["pause_reason"] = "high_failure_rate"
            _save_backfill_state(
                {
                    "next_offset": offset,
                    "last_batch": {"offset": offset, "stats": stats},
                    "paused": True,
                }
            )
            logger.warning(
                "timescale backfill paused at offset=%s failed=%s/%s",
                offset,
                codes_failed,
                codes_total,
            )
            break
        if not stats.get("codes_total"):
            break
        if codes_total < batch:
            offset += codes_total
            _save_backfill_state({"next_offset": offset, "completed": True, "last_stats": stats})
            break
        offset += batch
        batch_idx += 1
        _save_backfill_state({"next_offset": offset, "last_batch": {"offset": offset, "stats": stats}})
        if get_runtime_int("TIMESCALE_BACKFILL_BATCH_SLEEP_SEC", 0) > 0:
            time.sleep(get_runtime_int("TIMESCALE_BACKFILL_BATCH_SLEEP_SEC", 0))
    aggregated["total_batches"] = len(aggregated["batches"])
    aggregated["next_offset"] = offset
    return aggregated
