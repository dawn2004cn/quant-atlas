from __future__ import annotations
"""MySQL 日 K / qlib CSV / qlib_bin 覆盖快照。"""

from pathlib import Path
from typing import Any

from app.modules.data.services.tdx_code_cache import get_tdx_cn_universe
from app.modules.data.services.tdx_sync_checkpoint import load_failed_codes, load_ok_codes
from app.config import BASE_DIR, get_settings
from app.core.runtime_config import get_runtime
from app.core.utils.sql_utils import quote_identifier, validate_identifier


def _mysql_table_counts(suffix: str = "") -> dict[str, Any]:
    from app.config import get_settings
    from app.infrastructure.database.mysql_client import mysql_sync_connect

    settings = get_settings()
    if settings.mysql is None:
        return {"error": "mysql_not_configured"}
    out: dict[str, Any] = {"suffix": suffix or "(prod)", "tables": {}, "symbols_total": 0}
    if suffix not in ("", "_new"):
        return {"error": "invalid_suffix", "suffix": suffix}
    symbols: set[str] = set()
    if suffix == "":
        from app.modules.system.services.helpers.tdx_data_repository_access import (
            require_tdx_dayk_write_port,
        )

        codes = require_tdx_dayk_write_port().list_history_stock_codes()
        symbols.update(codes)
        out["symbols_total"] = len(symbols)
        for market in ("sh", "sz", "bj"):
            table = f"stock_history_{market}"
            n = sum(1 for c in codes if c.lower().startswith(market))
            out["tables"][table] = {"symbols": n}
    else:
        conn = mysql_sync_connect(settings.mysql, autocommit=True)
        try:
            cur = conn.cursor()
            for market in ("sh", "sz", "bj"):
                table = f"stock_history_{market}{suffix}"
                if not validate_identifier(table):
                    out["tables"][table] = {"error": "invalid_table_name"}
                    continue
                safe_table = quote_identifier(table)
                try:
                    cur.execute(f"SELECT COUNT(DISTINCT stock_code) FROM {safe_table}")
                    sym_n = int((cur.fetchone() or [0])[0] or 0)
                    out["tables"][table] = {"symbols": sym_n}
                except Exception as exc:  # noqa: BLE001
                    out["tables"][table] = {"error": str(exc)[:200]}
            out["symbols_total"] = sum(
                int(v.get("symbols") or 0)
                for v in out["tables"].values()
                if isinstance(v, dict) and "symbols" in v
            )
        finally:
            conn.close()
    return out


def _csv_snapshot() -> dict[str, Any]:
    export_dir = Path(get_runtime("QLIB_EXPORT_DIR", str(BASE_DIR / "instance" / "qlib_export")))
    if not export_dir.is_dir():
        return {"enabled": False, "export_dir": str(export_dir)}
    files = list(export_dir.glob("*.csv"))
    sample = export_dir / "SH600519.csv"
    if not sample.is_file():
        sample = export_dir / "sh600519.csv"
    return {
        "enabled": True,
        "export_dir": str(export_dir.resolve()),
        "csv_files": len(files),
        "sample_sh600519_exists": sample.is_file(),
    }


def _qlib_bin_snapshot() -> dict[str, Any]:
    bin_dir = Path(get_runtime("QLIB_BIN_DIR", str(BASE_DIR / "instance" / "qlib_bin")))
    if not bin_dir.is_dir():
        return {"enabled": False, "bin_dir": str(bin_dir)}
    features = bin_dir / "features"
    inst_count = 0
    if features.is_dir():
        inst_count = sum(1 for p in features.iterdir() if p.is_dir())
    cal = bin_dir / "calendars" / "day.txt"
    cal_days = 0
    if cal.is_file():
        cal_days = sum(1 for line in cal.read_text(encoding="utf-8").splitlines() if line.strip())
    return {
        "enabled": True,
        "bin_dir": str(bin_dir.resolve()),
        "instruments": inst_count,
        "calendar_days": cal_days,
    }


def collect_mysql_qlib_sync_status(*, include_mysql_counts: bool = False) -> dict[str, Any]:
    """MySQL + CSV + qlib_bin vs TDX universe（默认仅用检查点，避免 MySQL 大表 COUNT 超时）。"""
    settings = get_settings()
    universe = get_tdx_cn_universe()
    ok_codes = load_ok_codes()
    failed_codes = load_failed_codes()
    ok_n = len(ok_codes)
    fail_n = len(failed_codes)

    pending: list[str] = []
    mysql: dict[str, Any] = {
        "enabled": settings.use_mysql,
        "checkpoint_ok": ok_n,
        "checkpoint_failed": fail_n,
        "remaining_est": max(0, len(universe) - ok_n),
    }
    if not settings.use_mysql:
        pending.append("mysql_disabled")
    elif ok_n < len(universe) * 0.95 or fail_n > 0:
        pending.append("mysql_backfill")
    if fail_n > 0:
        pending.append("mysql_retry_failed")

    if include_mysql_counts and settings.use_mysql:
        try:
            mysql["production"] = _mysql_table_counts("")
            mysql["shadow_new"] = _mysql_table_counts("_new")
        except Exception as exc:  # noqa: BLE001
            mysql["counts_error"] = str(exc)[:300]

    csv = _csv_snapshot()
    csv_n = int(csv.get("csv_files") or 0)
    if csv.get("enabled") and csv_n < max(ok_n, len(universe) * 0.9):
        pending.append("csv_backfill")

    qlib = _qlib_bin_snapshot()
    if qlib.get("enabled") and int(qlib.get("instruments") or 0) < max(ok_n, len(universe) * 0.9):
        pending.append("qlib_bin_dump")

    return {
        "ok": not pending,
        "universe_size": len(universe),
        "checkpoint_ok_codes": ok_n,
        "checkpoint_failed_codes": fail_n,
        "mysql": mysql,
        "csv": csv,
        "qlib_bin": qlib,
        "pending_actions": pending,
    }
