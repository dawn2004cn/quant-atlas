from __future__ import annotations

"""单股同步与批量 run_sync 编排。"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from app.application.errors import ValidationError
from app.core.events import market_data_synced
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int
from app.domain.dto.service_result import GenericResponseDTO
from app.domain.dto.sync_dto import TdxSyncStatsDTO
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.domain.shared.tdx_paths import TdxLocalPaths
from app.modules.data.services.history_row_validator import validate_ohlcv_history_rows
from app.modules.data.services.tdx_dayk_adjustment import calculate_adjustment_factors
from app.modules.data.services.tdx_dayk_csv_writer import write_qlib_csv
from app.modules.data.services.tdx_dayk_sync_helpers import (
    cap_mysql_sync_workers,
    cap_timescale_sync_workers,
    is_transient_conn_error,
    normalize_ohlcv_rows,
    qlib_instrument_for,
)
from app.modules.data.services.tdx_dayk_sync_models import (
    SyncResult,
    default_enable_mysql_history,
    default_enable_timescale,
)
from app.modules.data.services.tdx_dayk_timescale_writer import (
    apply_timescale_counts,
    open_timescale_sync_session,
    persist_timescale_package,
    refresh_timescale_matviews,
)
from app.modules.data.services.timescale_sync_session import close_thread_timescale_session
from app.modules.system.services.helpers.tdx_data_repository_access import require_tdx_dayk_write_port
from app.modules.system.services.helpers.tdx_local_access import get_tdx_local_file_port

if TYPE_CHECKING:
    from app.config import AppSettings
    from app.modules.data.services.tdx_dayk_sync_service import TdxDaykSyncService

logger = get_logger(__name__)


def sync_one_stock(
    *,
    cn_symbol: str,
    raw_rows: list[dict[str, Any]],
    mysql_session: Any,
    csv_merge: bool,
    settings: AppSettings,
    export_dir: Path | str,
    ts_session: Any | None = None,
    enable_csv: bool = True,
    enable_timescale: bool = False,
) -> SyncResult:
    """同步单只股票数据（MySQL/CSV 写入原始数据，复权因子仅存储供 qlib bin 使用）."""
    stock_code = SymbolNormalizer.to_db_code(cn_symbol, market="CN")
    if not raw_rows:
        return SyncResult.skipped(stock_code)

    try:
        raw_rows = validate_ohlcv_history_rows(raw_rows)
    except ValidationError as exc:
        logger.warning("validate failed for %s: %s", cn_symbol, exc)
        return SyncResult.failed(stock_code, str(exc))

    result = SyncResult(stock_code=stock_code, status="ok")
    market = cn_symbol[:2]
    code = cn_symbol[-6:]
    factors = calculate_adjustment_factors(raw_rows, market, code)
    strict = get_runtime_bool("TDX_SYNC_STRICT_TARGETS", True)
    instrument = qlib_instrument_for(cn_symbol)

    try:
        if mysql_session:
            result.mysql_rows = mysql_session.write_bars(stock_code, raw_rows)
            result.factor_rows = mysql_session.write_factors(stock_code, factors)

        if enable_csv and raw_rows:
            csv_path = Path(export_dir) / f"{instrument}.csv"
            old_csv_path = csv_path.with_suffix(".csv.bak")
            if csv_path.exists():
                csv_path.rename(old_csv_path)
            try:
                n_csv, d0, d1 = write_qlib_csv(
                    Path(export_dir), instrument, raw_rows, merge=csv_merge
                )
                result.csv_rows = n_csv
                result.min_date = d0
                result.max_date = d1
            except Exception:
                if old_csv_path.exists():
                    old_csv_path.rename(csv_path)
                raise
            if old_csv_path.exists():
                old_csv_path.unlink()

        if enable_timescale:
            apply_timescale_counts(
                result,
                persist_timescale_package(
                    settings,
                    stock_code,
                    raw_rows,
                    factors,
                    ts_session=ts_session,
                ),
            )

        if strict:
            if enable_timescale and settings.use_timescaledb and result.timescale_rows <= 0:
                raise RuntimeError("timescale write produced no rows")
            if enable_csv and result.csv_rows <= 0:
                raise RuntimeError("csv write produced no rows")
            if mysql_session and result.mysql_rows <= 0:
                raise RuntimeError("mysql write produced no rows")
    except Exception as exc:
        logger.error("Sync failed for %s: %s", cn_symbol, exc)
        return SyncResult.failed(stock_code, str(exc))

    return result


def run_tdx_dayk_sync(
    service: TdxDaykSyncService,
    mode: str,
    codes: list[str],
    filter_rows: Callable[..., list[dict[str, Any]]],
    csv_merge: bool,
    dump_qlib_bin: bool,
    dump_max_workers: int,
    start_date: str | None = None,
    adjust_type: str = "forward",
    skip_latest_dates: bool = False,
    *,
    mysql_table_suffix: str = "",
    mysql_insert_only: bool = False,
    enable_csv: bool = True,
    enable_timescale: bool | None = None,
    enable_mysql: bool | None = None,
    write_checkpoint: bool = True,
) -> GenericResponseDTO:
    """执行同步流程（多线程并行处理股票）。每个 worker 使用独立 MySQL session."""
    if enable_mysql is False:
        dump_max_workers = cap_timescale_sync_workers(dump_max_workers)
    else:
        dump_max_workers = cap_mysql_sync_workers(dump_max_workers)

    root = service._require_tdx_root()
    paths = TdxLocalPaths(root)
    settings = service._settings
    if enable_timescale is None:
        enable_timescale = default_enable_timescale()
    if enable_mysql is None:
        enable_mysql = default_enable_mysql_history() and bool(settings.use_mysql)
    if enable_csv is None:
        enable_csv = True

    latest_dates: dict[str, str | None] = {}
    mysql_latest: dict[str, str | None] = {}
    ts_latest: dict[str, str | None] = {}
    if not skip_latest_dates:
        if settings.use_mysql and enable_mysql:
            port = require_tdx_dayk_write_port()
            sh = [c for c in codes if c.lower().startswith("sh")]
            sz = [c for c in codes if c.lower().startswith("sz")]
            bj = [c for c in codes if c.lower().startswith("bj")]

            def _query_market(cs: list[str], table: str) -> dict[str, str | None]:
                if not cs:
                    return {}
                session = port.open_sync_session(table_suffix=mysql_table_suffix)
                try:
                    return session.batch_get_latest_dates(cs)
                finally:
                    session.close()

            with ThreadPoolExecutor(max_workers=3) as pool:
                fut_map = {
                    pool.submit(_query_market, sh, "stock_history_sh"): sh,
                    pool.submit(_query_market, sz, "stock_history_sz"): sz,
                    pool.submit(_query_market, bj, "stock_history_bj"): bj,
                }
                for fut in as_completed(fut_map):
                    for key, value in fut.result().items():
                        mysql_latest[key] = value

        if enable_timescale and settings.use_timescaledb:
            from app.infrastructure.timeseries.ohlcv_latest_reader import (
                batch_get_latest_dates_timescale,
            )

            db_codes = [
                SymbolNormalizer.to_db_code(SymbolNormalizer.normalize_cn_symbol(c))
                for c in codes
            ]
            ts_latest = batch_get_latest_dates_timescale(db_codes)

        from app.modules.data.services.ohlcv_incremental_policy import min_latest_date_str

        for cn in codes:
            stock_code = SymbolNormalizer.to_db_code(SymbolNormalizer.normalize_cn_symbol(cn))
            latest_dates[stock_code] = min_latest_date_str(
                mysql_latest.get(stock_code), ts_latest.get(stock_code)
            )

    stats = {
        "mysql": 0,
        "csv": 0,
        "factors": 0,
        "timescale": 0,
        "timescale_factors": 0,
        "timescale_qfq": 0,
        "timescale_hfq": 0,
        "ok": 0,
        "skipped": 0,
        "failed": 0,
        "min_date": None,
        "max_date": None,
    }
    stats_lock = threading.Lock()
    failed_details: list[dict[str, str]] = []
    ok_codes_run: list[str] = []
    pending_ok_flush: list[str] = []
    checkpoint_enabled = write_checkpoint and get_runtime_bool("TDX_SYNC_CHECKPOINT", True)
    flush_every = max(1, get_runtime_int("TDX_SYNC_CHECKPOINT_FLUSH_EVERY", 10))
    done = 0
    total = len(codes)

    def _flush_checkpoint_progress(*, final: bool = False) -> None:
        if not checkpoint_enabled:
            return
        from app.modules.data.services.tdx_sync_checkpoint import flush_sync_checkpoint

        with stats_lock:
            batch = list(pending_ok_flush)
            pending_ok_flush.clear()
            failed_copy = list(failed_details)
            snap = dict(stats)
            processed = done
        if not batch and not failed_copy and not final:
            return
        flush_sync_checkpoint(
            ok_batch=batch or None,
            failed=failed_copy,
            last_run={
                "mode": mode,
                "partial": not final,
                "processed": processed,
                "codes_total": total,
                "ok_this_flush": len(batch),
                "failed_count": snap["failed"],
                "stats": {
                    "codes_ok": snap["ok"],
                    "codes_skipped": snap["skipped"],
                    "codes_failed": snap["failed"],
                    "mysql_rows": snap["mysql"],
                    "csv_written": snap["csv"],
                },
            },
        )
        if batch:
            logger.info(
                "checkpoint flush: +%d ok (processed %d/%d)",
                len(batch),
                processed,
                total,
            )

    conn_retries = max(1, get_runtime_int("TIMESCALE_SYNC_CONN_RETRIES", 3))

    def _lday_tail_for_sync(mode_name: str, latest: str | None) -> int | None:
        from app.modules.data.services.ohlcv_incremental_policy import tdx_lday_tail_bars

        return tdx_lday_tail_bars(mode_name, latest)

    def _process_one(cn_symbol: str) -> SyncResult:
        cn_symbol = SymbolNormalizer.normalize_cn_symbol(cn_symbol)
        stock_code = SymbolNormalizer.to_db_code(cn_symbol)
        last_err = "unknown"
        for attempt in range(conn_retries):
            session = None
            ts_session = None
            try:
                path = paths.lday_file_by_market(market=cn_symbol[:2], code6=cn_symbol[-6:])
                if not path.is_file():
                    return SyncResult.skipped(stock_code)

                latest = latest_dates.get(stock_code)
                lday_tail = _lday_tail_for_sync(mode, latest)
                rows = normalize_ohlcv_rows(
                    get_tdx_local_file_port().read_lday_file(path, tail=lday_tail)
                )
                filtered = filter_rows(rows, latest)
                if not filtered:
                    return SyncResult.skipped(stock_code)

                session = (
                    require_tdx_dayk_write_port().open_sync_session(
                        table_suffix=mysql_table_suffix,
                        insert_only=mysql_insert_only,
                    )
                    if settings.use_mysql and enable_mysql
                    else None
                )
                ts_session = (
                    open_timescale_sync_session()
                    if enable_timescale and settings.use_timescaledb
                    else None
                )
                try:
                    res = sync_one_stock(
                        cn_symbol=cn_symbol,
                        raw_rows=filtered,
                        mysql_session=session,
                        csv_merge=csv_merge,
                        settings=settings,
                        export_dir=service._qlib.export_dir,
                        ts_session=ts_session,
                        enable_csv=enable_csv,
                        enable_timescale=enable_timescale,
                    )
                    if res.status == "ok":
                        if session:
                            session.commit()
                        if ts_session:
                            ts_session.commit()
                    else:
                        if session:
                            session.rollback()
                        if ts_session:
                            ts_session.rollback()
                    return res
                except Exception:
                    if session:
                        session.rollback()
                    if ts_session:
                        ts_session.rollback()
                    raise
                finally:
                    if session:
                        session.close()
            except Exception as exc:
                last_err = str(exc)
                if (
                    attempt < conn_retries - 1
                    and enable_timescale
                    and is_transient_conn_error(last_err)
                ):
                    close_thread_timescale_session()
                    time.sleep(1.5 * (attempt + 1))
                    continue
                logger.error("同步失败 %s: %s", cn_symbol, exc)
                return SyncResult.failed(stock_code, last_err)
        return SyncResult.failed(stock_code, last_err)

    futures: dict[Any, str] = {}
    with ThreadPoolExecutor(max_workers=dump_max_workers) as pool:
        for sym in codes:
            futures[pool.submit(_process_one, sym)] = sym

        for fut in as_completed(futures):
            done += 1
            res = fut.result()
            with stats_lock:
                if res.status == "skipped":
                    stats["skipped"] += 1
                    continue
                if res.status == "failed":
                    stats["failed"] += 1
                    failed_details.append(
                        {"code": res.stock_code, "error": res.error or "unknown"}
                    )
                    continue
                if res.status == "ok" and (
                    res.mysql_rows > 0 or res.csv_rows > 0 or res.timescale_rows > 0
                ):
                    ok_codes_run.append(res.stock_code)
                    pending_ok_flush.append(res.stock_code)
                stats["mysql"] += res.mysql_rows
                stats["factors"] += res.factor_rows
                stats["timescale"] += res.timescale_rows
                stats["timescale_factors"] += res.timescale_factor_rows
                stats["timescale_qfq"] += res.timescale_qfq_rows
                stats["timescale_hfq"] += res.timescale_hfq_rows
                if res.mysql_rows > 0 or res.csv_rows > 0 or res.timescale_rows > 0:
                    stats["ok"] += 1
                if res.csv_rows > 0:
                    stats["csv"] += 1
                if res.min_date:
                    if stats["min_date"] is None or res.min_date < stats["min_date"]:
                        stats["min_date"] = res.min_date
                if res.max_date:
                    if stats["max_date"] is None or res.max_date > stats["max_date"]:
                        stats["max_date"] = res.max_date
            if total > 100 and done % 100 == 0:
                logger.info("已处理 %d/%d 只股票", done, total)
            if checkpoint_enabled and (done % flush_every == 0 or done == total):
                _flush_checkpoint_progress(final=done == total)

        if settings.use_timescaledb:
            for _ in range(dump_max_workers):
                pool.submit(close_thread_timescale_session)

    if enable_timescale:
        refresh_timescale_matviews(settings)

    qlib_dump: dict[str, Any] | None = None
    if dump_qlib_bin and stats["csv"] > 0:
        try:
            # CSV → qlib_bin（不再经 MySQL）
            qlib_dump = service._qlib.dump_to_qlib_bin(
                max_workers=max(1, int(dump_max_workers or 8)),
                incremental=True,
            )
            if not isinstance(qlib_dump, dict) or not qlib_dump.get("ok", True):
                stats["failed"] = max(stats["failed"], 1)
                logger.warning("qlib_bin dump reported failure: %s", qlib_dump)
            else:
                logger.info("qlib_bin dumped from CSV successfully")
        except Exception as exc:
            stats["failed"] = max(stats["failed"], 1)
            qlib_dump = {"ok": False, "error": str(exc)}
            logger.warning("qlib_bin dump failed: %s", exc)
    elif dump_qlib_bin and stats["csv"] == 0:
        qlib_dump = {"ok": True, "skipped": True, "reason": "no_csv_written"}
        logger.info("qlib_bin dump skipped: no CSV rows written this run")

    sync_stats = TdxSyncStatsDTO(
        codes_total=len(codes),
        codes_ok=stats["ok"],
        codes_skipped=stats["skipped"],
        codes_failed=stats["failed"],
        mysql_rows=stats["mysql"],
        csv_written=stats["csv"],
        date_min=stats["min_date"] or "",
        date_max=stats["max_date"] or "",
        timescale_rows=stats["timescale"],
        timescale_factor_rows=stats["timescale_factors"],
        timescale_qfq_rows=stats["timescale_qfq"],
        timescale_hfq_rows=stats["timescale_hfq"],
    )
    market_data_synced.send(service, stats=sync_stats.model_dump())

    checkpoint_paths: dict[str, str] = {}
    if checkpoint_enabled:
        from app.modules.data.services.tdx_sync_checkpoint import checkpoint_dir, save_last_run

        _flush_checkpoint_progress(final=True)
        failed_path = checkpoint_dir() / "failed_codes.txt"
        checkpoint_paths = {
            "checkpoint_dir": str(checkpoint_dir()),
            "failed_codes_file": str(failed_path),
            "ok_codes_file": str(checkpoint_dir() / "ok_codes.txt"),
        }
        save_last_run(
            {
                "mode": mode,
                "partial": False,
                "stats": sync_stats.model_dump(),
                "failed_count": stats["failed"],
                "ok_this_run": len(ok_codes_run),
                "failed_samples": failed_details[:20],
            }
        )

    return {
        "ok": stats["failed"] == 0,
        "mode": mode,
        "stats": sync_stats.model_dump(),
        "factors_written": stats["factors"],
        "skipped": stats["skipped"],
        "failed": stats["failed"],
        "errors": stats["failed"],
        "failed_codes": [item["code"] for item in failed_details],
        "checkpoint": checkpoint_paths,
        "qlib_bin": qlib_dump,
    }
