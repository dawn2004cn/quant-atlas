from __future__ import annotations
"""Orchestrate QuestDB + ClickHouse OHLCV sync from TDX lday only."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any, Literal

from app.modules.data.services.clickhouse_ohlcv_sync_service import (
    clickhouse_sync_enabled,
    delete_clickhouse_date_range,
    write_bars_clickhouse,
)
from app.modules.data.services.ohlcv_incremental_policy import (
    dedupe_bars_by_date,
    verify_bars_cover_window,
)
from app.modules.data.services.ohlcv_sync_common import (
    fetch_cn_daily_bars,
    resolve_sync_symbols,
    symbol_incremental_start,
    sync_limits,
)
from app.modules.data.services.questdb_ohlcv_writer import (
    delete_questdb_date_range,
    questdb_table,
    write_bars_questdb,
)
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int
from app.infrastructure.database.timeseries_settings import (
    load_clickhouse_settings,
    load_questdb_settings,
)

logger = get_logger(__name__)

SyncMode = Literal["full", "incremental"]


def _sync_one_symbol(
    code: str,
    end_d: date,
    lookback_days: int,
    *,
    mode: SyncMode,
    want_q: bool,
    want_ch: bool,
    q_table: str,
    upsert_delete: bool,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "code": code,
        "questdb_rows": 0,
        "clickhouse_rows": 0,
        "skipped": False,
        "up_to_date": False,
    }
    if mode == "incremental":
        start_d = symbol_incremental_start(
            code,
            end_d,
            lookback_days,
            want_questdb=want_q,
            want_clickhouse=want_ch,
        )
        if start_d is None:
            out["skipped"] = True
            out["up_to_date"] = True
            return out
    else:
        start_d = end_d - timedelta(days=lookback_days)

    bars = dedupe_bars_by_date(fetch_cn_daily_bars(code, start_d, end_d))
    cover = verify_bars_cover_window(bars, start_d, end_d, code=code)
    if not cover.get("ok"):
        if mode == "incremental" and cover.get("reason") == "empty_bars":
            out["skipped"] = True
            out["up_to_date"] = True
            return out
        out["error"] = cover.get("reason", "no_bars")
        return out

    start_s = start_d.isoformat()
    end_s = end_d.isoformat()
    if upsert_delete:
        if want_q:
            delete_questdb_date_range(code, start_s, end_s, q_table)
        if want_ch:
            delete_clickhouse_date_range(code, start_s, end_s)

    if want_q:
        out["questdb_rows"] = write_bars_questdb(code, bars, q_table)
    if want_ch:
        out["clickhouse_rows"] = write_bars_clickhouse(code, bars)
    return out


def run_timeseries_ohlcv_sync(
    *,
    limit: int | None = None,
    symbols: list[str] | None = None,
    lookback_days: int | None = None,
    targets: list[str] | None = None,
    offset: int = 0,
    skip_existing: bool | None = None,
    max_symbols_cap: int = 2000,
    workers: int | None = None,
    mode: SyncMode | None = None,
    all_market: bool | None = None,
) -> dict[str, Any]:
    """Sync to QuestDB (ILP) and optionally ClickHouse (INSERT)."""
    if not get_runtime_bool("ENABLE_QUESTDB_SYNC", get_runtime_bool("ENABLE_TIMESERIES_SYNC", True)):
        return {"ok": True, "skipped": True, "reason": "sync_disabled"}

    want_q = load_questdb_settings() is not None
    if want_q:
        from app.modules.data.services.questdb_table_layout import load_questdb_ohlcv_layout

        load_questdb_ohlcv_layout(questdb_table())
    want_ch = clickhouse_sync_enabled()
    if targets:
        want_q = want_q and "questdb" in targets
        want_ch = want_ch and "clickhouse" in targets
    if not want_q and not want_ch:
        return {"ok": False, "error": "no_timeseries_target"}

    sync_mode: SyncMode = mode or (
        "incremental" if get_runtime_bool("TIMESERIES_SYNC_INCREMENTAL", True) else "full"
    )
    if skip_existing is False:
        sync_mode = "full"

    if want_q and sync_mode == "full":
        from app.modules.data.services.questdb_ohlcv_writer import ensure_questdb_dedup

        ensure_questdb_dedup()

    env_all = get_runtime_bool("TIMESERIES_SYNC_ALL_MARKET", False)
    use_all = all_market if all_market is not None else env_all
    paginated = limit is not None and limit > 0
    if sync_mode == "incremental" and limit is None and env_all:
        use_all = True
        paginated = False

    eff_limit = limit
    if use_all and not paginated and (limit is None or limit <= 0):
        eff_limit = 0

    lim, days = sync_limits(
        limit=eff_limit,
        lookback_days=lookback_days,
        max_symbols_cap=max_symbols_cap,
        all_market=use_all and not paginated,
    )
    end_d = date.today()
    codes = resolve_sync_symbols(lim, symbols, offset=offset, all_market=use_all and not paginated)
    if not codes:
        return {
            "ok": False,
            "error": "no_symbols",
            "hint": "配置 TDX_ROOT_PATH 或 TIMESERIES_SYNC_SYMBOLS；标的来自 TDX vipdoc lday 扫描",
        }

    from app.infrastructure.timeseries.sync_snapshot import (
        clear_timeseries_sync_progress,
        set_timeseries_sync_progress,
    )

    set_timeseries_sync_progress(
        status="running",
        symbols_total=len(codes),
        symbols_done=0,
        source="sync",
        message="ohlcv_sync_started",
    )

    upsert_delete = get_runtime_bool("TIMESERIES_UPSERT_DELETE_RANGE", True)
    q_table = questdb_table()
    pool_workers = max(1, min(workers or get_runtime_int("TIMESERIES_SYNC_WORKERS", 4), 16))

    result: dict[str, Any] = {
        "ok": False,
        "mode": sync_mode,
        "symbols_requested": len(codes),
        "offset": offset,
        "lookback_days": days,
        "upsert_delete_range": upsert_delete,
        "workers": pool_workers,
        "questdb": {"enabled": want_q, "table": q_table, "symbols_ok": 0, "rows_written": 0, "skipped": 0},
        "clickhouse": {"enabled": want_ch, "symbols_ok": 0, "rows_written": 0, "skipped": 0},
        "up_to_date": 0,
        "failed_samples": [],
    }

    def _merge(item: dict[str, Any]) -> None:
        code = item.get("code", "")
        if item.get("up_to_date"):
            result["up_to_date"] += 1
        elif item.get("skipped"):
            if want_q:
                result["questdb"]["skipped"] += 1
            if want_ch:
                result["clickhouse"]["skipped"] += 1
        else:
            qr = int(item.get("questdb_rows") or 0)
            cr = int(item.get("clickhouse_rows") or 0)
            if qr > 0:
                result["questdb"]["symbols_ok"] += 1
                result["questdb"]["rows_written"] += qr
            if cr > 0:
                result["clickhouse"]["symbols_ok"] += 1
                result["clickhouse"]["rows_written"] += cr
            if item.get("error") and len(result["failed_samples"]) < 10:
                result["failed_samples"].append({"code": code, "error": item["error"]})
        result["symbols_processed"] = int(result.get("symbols_processed") or 0) + 1
        done = result["symbols_processed"]
        if done == len(codes) or done % 20 == 0:
            set_timeseries_sync_progress(
                status="running",
                symbols_total=len(codes),
                symbols_done=done,
                source="sync",
            )

    common_kw = dict(
        end_d=end_d,
        lookback_days=days,
        mode=sync_mode,
        want_q=want_q,
        want_ch=want_ch,
        q_table=q_table,
        upsert_delete=upsert_delete,
    )

    if pool_workers <= 1 or len(codes) < 8:
        for code in codes:
            _merge(_sync_one_symbol(code, **common_kw))
    else:
        with ThreadPoolExecutor(max_workers=pool_workers) as pool:
            futs = {pool.submit(_sync_one_symbol, code, **common_kw): code for code in codes}
            for fut in as_completed(futs):
                try:
                    _merge(fut.result())
                except Exception as exc:  # noqa: BLE001
                    code = futs[fut]
                    if len(result["failed_samples"]) < 10:
                        result["failed_samples"].append({"code": code, "error": str(exc)[:200]})

    has_writes = (
        result["questdb"]["rows_written"] > 0 or result["clickhouse"]["rows_written"] > 0
    )
    no_failures = not result["failed_samples"]
    result["ok"] = no_failures and (
        has_writes or (sync_mode == "incremental" and result["up_to_date"] > 0)
    )
    try:
        from app.infrastructure.timeseries.sync_snapshot import record_timeseries_sync_snapshot

        record_timeseries_sync_snapshot(result, source="sync")
    except Exception as exc:  # noqa: BLE001
        logger.debug("timeseries sync snapshot skipped: %s", exc)
    finally:
        clear_timeseries_sync_progress()
    return result


def run_timeseries_ohlcv_backfill(
    *,
    batch_size: int | None = None,
    max_batches: int | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Paginated full backfill from TDX lday universe (offset + batch)."""
    batch = batch_size or get_runtime_int("TIMESERIES_BACKFILL_BATCH", 200)
    batches = max_batches or get_runtime_int("TIMESERIES_BACKFILL_MAX_BATCHES", 0)
    cap = kwargs.pop("max_symbols_cap", 50_000)
    kwargs.setdefault("mode", "full")
    kwargs.setdefault("skip_existing", False)
    kwargs.setdefault("all_market", True)
    aggregated: dict[str, Any] = {
        "ok": True,
        "batches": [],
        "questdb": {"rows_written": 0, "symbols_ok": 0},
        "clickhouse": {"rows_written": 0, "symbols_ok": 0},
    }
    offset = int(kwargs.pop("offset", 0) or 0)
    batch_idx = 0
    while True:
        if batches > 0 and batch_idx >= batches:
            break
        chunk = run_timeseries_ohlcv_sync(
            limit=batch,
            offset=offset,
            max_symbols_cap=cap,
            **kwargs,
        )
        aggregated["batches"].append({"offset": offset, **chunk})
        if not chunk.get("symbols_requested"):
            break
        for key in ("questdb", "clickhouse"):
            if key in chunk and key in aggregated:
                aggregated[key]["rows_written"] += chunk[key].get("rows_written", 0)
                aggregated[key]["symbols_ok"] += chunk[key].get("symbols_ok", 0)
        if chunk.get("ok"):
            aggregated["ok"] = True
        req = int(chunk.get("symbols_requested") or 0)
        if req == 0:
            break
        if req < batch:
            break
        offset += batch
        batch_idx += 1
        logger.info(
            "backfill batch %s offset=%s q=%s ch=%s",
            batch_idx,
            offset,
            chunk.get("questdb", {}).get("rows_written"),
            chunk.get("clickhouse", {}).get("rows_written"),
        )

    aggregated["total_batches"] = len(aggregated["batches"])
    aggregated["next_offset"] = offset
    try:
        from app.infrastructure.timeseries.sync_snapshot import record_timeseries_sync_snapshot

        record_timeseries_sync_snapshot(aggregated, source="backfill")
    except Exception as exc:  # noqa: BLE001
        logger.debug("backfill sync snapshot skipped: %s", exc)
    return aggregated
