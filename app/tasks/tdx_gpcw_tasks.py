from __future__ import annotations

"""TDX gpcw 财务数据入库 Celery 任务

- 存量入库 (backfill): 扫描所gpcw*.dat 历史文件，导入全量股票全期数
- 新增入库 (incremental): 仅处理最新的 gpcw*.dat 文件（通常每季度更新一次）
"""


import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

from ..celery_app import celery as _celery
from ..config import get_settings
from ..core.runtime_config import get_runtime, get_runtime_int
from .task_wiring import create_cn_tdx_gpcw_provider, create_tdx_gpcw_task_repository, ensure_tdx_gpcw_audit_table

logger = get_logger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _get_repo() -> Any:
    return create_tdx_gpcw_task_repository()


def _ensure_audit_table() -> None:
    ensure_tdx_gpcw_audit_table()


def _get_batch_size() -> int:
    return max(10, get_runtime_int("TDX_GPCW_BATCH_SIZE", 50))


def _get_stock_filter() -> set[str] | None:
    raw = get_runtime("TDX_GPCW_STOCK_FILTER", "")
    if not raw:
        return None
    return {c.strip() for c in raw.split(",") if c.strip()}


def _code_to_market(code6: str) -> str:
    c = code6.lstrip("0")
    if c.startswith("6") or c.startswith("9"):
        return "sh"
    return "sz"


def _to_indexed_code(code6: str, market: str) -> str:
    return f"{market}{code6}"


def _build_rows(
    provider: Any,
    all_periods: list[dict[str, Any]],
    code6: str,
    stock_filter: set[str] | None,
) -> list[dict[str, Any]]:
    market = _code_to_market(code6)
    indexed_code = _to_indexed_code(code6, market)
    rows = []
    for period_data in all_periods:
        if not period_data.get("ok"):
            continue
        raw_values = period_data.get("fields", [])
        named = provider.get_named_fields(raw_values)
        rows.append({
            "code": code6,
            "indexed_code": indexed_code,
            "market": market,
            "report_date": period_data["report_date"],
            "source_file": period_data["file"],
            "fields": named,
        })
    if stock_filter and code6 not in stock_filter:
        return []
    return rows


def _process_file(
    provider: Any,
    fpath: Path,
    repo: Any,
    task_type: str,
    stock_filter: set[str] | None,
    batch_size: int,
) -> dict[str, Any]:
    from pytdx.reader import HistoryFinancialReader

    started_at = time.time()
    status = "running"
    error_msg = None
    stocks_processed = 0
    rows_written = 0
    rows_updated = 0
    rows_skipped = 0

    try:
        reader = HistoryFinancialReader()
        df = reader.get_df(str(fpath))
        if df is None or df.empty:
            raise ValueError(f"Empty DataFrame from {fpath.name}")

        report_date = int(df.iloc[0, 0]) if hasattr(df.iloc[0, 0], "__int__") else 0
        all_codes = list(df.index)
        stock_rows = []

        for code6 in all_codes:
            if stock_filter and code6 not in stock_filter:
                continue
            try:
                row = df.loc[code6]
                rd = int(row.iloc[0]) if hasattr(row.iloc[0], "__int__") else report_date
                raw_values = row.iloc[1:585].fillna(0).tolist()
                named = provider.get_named_fields(raw_values)
                market = _code_to_market(code6)
                stock_rows.append({
                    "code": code6,
                    "indexed_code": _to_indexed_code(code6, market),
                    "market": market,
                    "report_date": rd,
                    "source_file": fpath.name,
                    "fields": named,
                })
                stocks_processed += 1
            except Exception as exc:
                rows_skipped += 1
                logger.debug("skip stock %s: %s", code6, exc)

        written, updated, errors = repo.upsert_batch(stock_rows, batch_size=batch_size)
        rows_written = written
        rows_updated = updated
        rows_skipped += errors
        status = "success"
    except Exception as exc:
        status = "failed"
        error_msg = str(exc)
        logger.error("gpcw import failed for %s: %s", fpath.name, exc)

    duration = time.time() - started_at
    try:
        repo.record_audit(
            task_type=task_type,
            source_file=fpath.name,
            report_date=0,
            stocks_processed=stocks_processed,
            rows_written=rows_written,
            rows_skipped=rows_skipped,
            rows_updated=rows_updated,
            status=status,
            error_msg=error_msg,
            duration_sec=duration,
        )
    except Exception as e:
        logger.warning("tdx_gpcw_tasks.py._process_file: %s", e)

    return {
        "file": fpath.name,
        "status": status,
        "stocks_processed": stocks_processed,
        "rows_written": rows_written,
        "rows_updated": rows_updated,
        "rows_skipped": rows_skipped,
        "duration_sec": round(duration, 2),
        "error": error_msg,
    }


@_celery.task(
    name="app.tasks.tdx_gpcw_tasks.backfill_tdx_gpcw_full",
    bind=True,
    acks_late=True,
    time_limit=3600,       # 1小时硬限
    soft_time_limit=3300,  # 55分钟软限制，允许任务自行收尾
)
def backfill_tdx_gpcw_full(
    self,
    stock_filter_csv: str = "",
    max_files: int = 0,
) -> dict[str, Any]:
    """TDX gpcw 全量存量入库：扫描所有历gpcw*.dat，导入每只股票每期数据

    - `stock_filter_csv`: 逗号分隔股票代码列表（如 "688313,000001"），空则全部
    - `max_files`: 最大处理文件数=不限制）
    """
    logger.info("TDX gpcw full backfill started (max_files=%s, stock_filter=%s)", max_files, stock_filter_csv)
    _ensure_audit_table()
    repo = _get_repo()
    s = get_settings()
    tdx_path = s.tdx_root_path
    if not tdx_path:
        return {"ok": False, "error": "TDX_ROOT_PATH not configured"}

    stock_filter: set[str] | None = None
    if stock_filter_csv:
        stock_filter = {c.strip() for c in stock_filter_csv.split(",") if c.strip()}
    batch_size = _get_batch_size()

    provider = create_cn_tdx_gpcw_provider(tdx_root_path=tdx_path)
    gpcw_dir = provider.gpcw_dir
    if gpcw_dir is None or not gpcw_dir.is_dir():
        return {"ok": False, "error": f"gpcw directory not found: {gpcw_dir}"}

    files = provider._scan_dat_files(gpcw_dir)
    files.sort(key=lambda x: x[1])
    files = [f for f in files if f[2] >= 500]
    if max_files > 0:
        files = files[:max_files]

    results = []
    for fpath, report_date, max_count in files:
        logger.info("Processing %s (date=%s, stocks=%s)", fpath.name, report_date, max_count)
        result = _process_file(provider, fpath, repo, "full", stock_filter, batch_size)
        results.append(result)
        logger.info(
            "  -> stocks=%s rows=%s updated=%s duration=%.1fs",
            result["stocks_processed"],
            result["rows_written"],
            result["rows_updated"],
            result["duration_sec"],
        )

    total_stocks = sum(r["stocks_processed"] for r in results)
    total_written = sum(r["rows_written"] for r in results)
    total_updated = sum(r["rows_updated"] for r in results)
    logger.info(
        "TDX gpcw full backfill done: %d files, %d stocks, %d rows written, %d updated",
        len(results), total_stocks, total_written, total_updated,
    )
    return {
        "ok": True,
        "files_processed": len(results),
        "total_stocks": total_stocks,
        "total_written": total_written,
        "total_updated": total_updated,
        "details": results,
    }


@_celery.task(
    name="app.tasks.tdx_gpcw_tasks.import_tdx_gpcw_latest",
    bind=True,
    acks_late=True,
    time_limit=600,
)
def import_tdx_gpcw_latest(
    self,
    stock_filter_csv: str = "",
    target_date: int = 0,
) -> dict[str, Any]:
    """TDX gpcw 新增入库：仅处理最新（或指定日期）gpcw*.dat 文件

    - `stock_filter_csv`: 逗号分隔股票代码列表
    - `target_date`: 指定日期（如 20250930），0 则取最新有效文
    """
    logger.info("TDX gpcw incremental import started (target_date=%s)", target_date)
    _ensure_audit_table()
    repo = _get_repo()
    s = get_settings()
    tdx_path = s.tdx_root_path
    if not tdx_path:
        return {"ok": False, "error": "TDX_ROOT_PATH not configured"}

    stock_filter: set[str] | None = None
    if stock_filter_csv:
        stock_filter = {c.strip() for c in stock_filter_csv.split(",") if c.strip()}
    batch_size = _get_batch_size()

    provider = create_cn_tdx_gpcw_provider(tdx_root_path=tdx_path)
    gpcw_dir = provider.gpcw_dir
    if gpcw_dir is None or not gpcw_dir.is_dir():
        return {"ok": False, "error": f"gpcw directory not found: {gpcw_dir}"}

    files = provider._scan_dat_files(gpcw_dir)
    files.sort(key=lambda x: x[1], reverse=True)
    files = [f for f in files if f[2] >= 500]

    target_file = None
    for fpath, report_date, _max_count in files:
        if target_date > 0 and report_date != target_date:
            continue
        target_file = fpath
        break

    if target_file is None:
        return {"ok": False, "error": f"No valid file found for date={target_date}"}

    logger.info("Using file: %s (date=%s)", target_file.name, target_date)
    result = _process_file(provider, target_file, repo, "incremental", stock_filter, batch_size)
    logger.info(
        "TDX gpcw incremental done: stocks=%s rows=%s updated=%s duration=%.1fs",
        result["stocks_processed"], result["rows_written"], result["rows_updated"], result["duration_sec"],
    )
    return {
        "ok": result["status"] == "success",
        "file": result["file"],
        "stocks_processed": result["stocks_processed"],
        "rows_written": result["rows_written"],
        "rows_updated": result["rows_updated"],
        "rows_skipped": result["rows_skipped"],
        "duration_sec": result["duration_sec"],
        "error": result.get("error"),
    }


@_celery.task(name="app.tasks.tdx_gpcw_tasks.import_tdx_gpcw_for_stock")
def import_tdx_gpcw_for_stock(
    code: str,
) -> dict[str, Any]:
    """TDX gpcw 单股入库：将指定股票所有期（最6期）数据导入 MySQL

    - `code`: 6位股票代码（"688313"
    """
    logger.info("TDX gpcw single stock import: %s", code)
    _ensure_audit_table()
    repo = _get_repo()
    s = get_settings()
    tdx_path = s.tdx_root_path
    if not tdx_path:
        return {"ok": False, "error": "TDX_ROOT_PATH not configured"}

    provider = create_cn_tdx_gpcw_provider(tdx_root_path=tdx_path)
    gpcw_dir = provider.gpcw_dir
    if gpcw_dir is None or not gpcw_dir.is_dir():
        return {"ok": False, "error": "gpcw directory not found"}

    all_periods = provider.get_all_periods(code)
    if not all_periods:
        return {"ok": False, "error": f"No data found for {code}"}

    rows = _build_rows(provider, all_periods, code.strip()[-6:].lstrip("0"), None)
    written, updated, errors = repo.upsert_batch(rows)
    logger.info("TDX gpcw single stock %s: %d periods, written=%d updated=%d", code, len(rows), written, updated)
    return {
        "ok": True,
        "code": code,
        "periods": len(rows),
        "rows_written": written,
        "rows_updated": updated,
        "rows_errors": errors,
    }
