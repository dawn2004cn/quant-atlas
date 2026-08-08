#!/usr/bin/env python3
"""Ensure QuestDB OHLCV table uses SYMBOL(stock_code) for fast point lookups.

Usage:
  python scripts/migrations/questdb_ohlcv_symbol_index.py [--dry-run|--check] [--no-create]

Requires QUESTDB_* env (see app/infrastructure/database/timeseries_settings.py).
Idempotent: skips when column is already SYMBOL or table missing (unless create enabled).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.infrastructure.database.timeseries_settings import load_questdb_settings
from app.infrastructure.timeseries.timeseries_factory import create_questdb_adapter
from app.modules.data.services.ohlcv_sync_common import safe_table_name

logger = get_logger(__name__)

DDL_PATH = ROOT / "scripts" / "questdb_stock_history_ddl.sql"


def _column_type(adapter, table: str, column: str) -> str | None:
    rows = adapter.execute_raw_query(f"SHOW COLUMNS FROM {table}")
    for row in rows or []:
        if str(row.get("column") or "") == column:
            return str(row.get("type") or "").upper()
    return None


def _table_exists(adapter, table: str) -> bool:
    try:
        adapter.execute_raw_query(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except Exception:
        return False


def migrate(*, dry_run: bool = False, create_if_missing: bool = True) -> dict[str, str]:
    cfg = load_questdb_settings()
    if cfg is None:
        return {"status": "skipped", "reason": "questdb_not_configured"}

    table = safe_table_name(get_runtime("QUESTDB_OHLCV_TABLE", "stock_history"), "stock_history")
    adapter = create_questdb_adapter(cfg)
    if adapter is None or not adapter.connect():
        return {"status": "error", "reason": "questdb_connect_failed"}

    try:
        if not _table_exists(adapter, table):
            if not create_if_missing:
                return {"status": "skipped", "reason": f"table_missing:{table}"}
            ddl = DDL_PATH.read_text(encoding="utf-8")
            if dry_run:
                return {"status": "dry_run", "action": "create_table", "table": table}
            adapter.execute_raw_query(ddl)
            return {"status": "ok", "action": "create_table", "table": table}

        col_type = _column_type(adapter, table, "stock_code")
        if col_type and "SYMBOL" in col_type:
            return {"status": "ok", "action": "noop", "table": table, "stock_code_type": col_type}

        sql = f"ALTER TABLE {table} ALTER COLUMN stock_code SYMBOL"
        if dry_run:
            return {
                "status": "dry_run",
                "action": "alter_column",
                "table": table,
                "from_type": col_type or "unknown",
                "sql": sql,
            }
        adapter.execute_raw_query(sql)
        return {
            "status": "ok",
            "action": "alter_column",
            "table": table,
            "from_type": col_type or "unknown",
        }
    finally:
        adapter.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned action only (no DDL)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Same as --dry-run; exit 0 when SYMBOL already in place or dry-run planned",
    )
    parser.add_argument(
        "--no-create",
        action="store_true",
        help="Do not create missing OHLCV table",
    )
    args = parser.parse_args()
    dry_run = bool(args.dry_run or args.check)
    result = migrate(dry_run=dry_run, create_if_missing=not args.no_create)
    print(result)
    status = result.get("status")
    if status == "error":
        return 1
    if args.check and status == "dry_run":
        # Check mode: pending ALTER is a soft signal (exit 2) for ops scripts.
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
