#!/usr/bin/env python3
"""将库内 ``CN:sh600519`` / ``CN:600519`` 等迁移为 ``sh600519``（可重复执行）。

用法（项目根目录）:
  python scripts/migrations/strip_cn_prefix_stock_codes.py --dry-run
  python scripts/migrations/strip_cn_prefix_stock_codes.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect
from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer


def _canonical(raw: str) -> str:
    return SymbolNormalizer.to_db_code(raw)


def _migrate_table(cur, table: str, column: str, *, apply: bool) -> int:
    cur.execute(
        f"SELECT DISTINCT {column} FROM {table} WHERE {column} LIKE %s OR {column} LIKE %s",
        ("CN:%", "cn:%"),
    )
    rows = cur.fetchall()
    changed = 0
    for row in rows:
        if isinstance(row, dict):
            old = row.get(column) or row.get(column.upper())
        elif isinstance(row, (list, tuple)):
            old = row[0]
        else:
            old = row
        if not old:
            continue
        new = _canonical(str(old))
        if new == old:
            continue
        changed += 1
        if apply:
            cur.execute(
                f"UPDATE {table} SET {column}=%s WHERE {column}=%s",
                (new, old),
            )
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="写入数据库（默认仅预览）")
    parser.add_argument("--dry-run", action="store_true", help="仅统计（默认）")
    args = parser.parse_args()
    apply = bool(args.apply)
    if not apply:
        print("DRY RUN — 加 --apply 才会写入")

    settings = AppSettings.from_env()
    if not settings.use_mysql or settings.mysql is None:
        print("MySQL 未启用，跳过")
        return 1

    targets = [
        ("cn_stock_basics", "symbol"),
        ("tdx_block_items", "symbol"),
        ("tdx_watchlist_items", "symbol"),
        ("stock_history_sh", "stock_code"),
        ("stock_history_sz", "stock_code"),
        ("stock_history_bj", "stock_code"),
    ]

    conn = mysql_connect(settings.mysql)
    try:
        with conn.cursor() as cur:
            total = 0
            for table, col in targets:
                try:
                    n = _migrate_table(cur, table, col, apply=apply)
                    print(f"{table}.{col}: {n} distinct codes to migrate")
                    total += n
                except Exception as exc:
                    print(f"{table}.{col}: skip ({exc})")
            if apply:
                conn.commit()
                print(f"committed, ~{total} code variants updated")
            else:
                print(f"would touch ~{total} distinct legacy codes")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
