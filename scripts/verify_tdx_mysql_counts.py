"""Quick sanity check for TDX base tables in MySQL (no writes).

Examples:
  python scripts/verify_tdx_mysql_counts.py
  python scripts/verify_tdx_mysql_counts.py --symbol sh600519
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect
from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--symbol",
        default="",
        help="Optional: print block memberships for a symbol (e.g. sh600519)",
    )
    p.add_argument(
        "--stats",
        action="store_true",
        help="Print counts for tdx_block_items (all vs any remaining CN: prefixed)",
    )
    p.add_argument(
        "--extra",
        action="store_true",
        help="Print counts for tdx_watchlists / finance snapshots",
    )
    args = p.parse_args()

    s = AppSettings.from_env()
    if not s.use_mysql or s.mysql is None:
        print("mysql_not_enabled")
        return 2

    conn = mysql_connect(s.mysql)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM cn_stock_basics")
            stocks = int((cur.fetchone() or {}).get("c") or 0)
            cur.execute("SELECT COUNT(*) AS c FROM tdx_blocks")
            blocks = int((cur.fetchone() or {}).get("c") or 0)
            cur.execute("SELECT COUNT(*) AS c FROM tdx_block_items")
            items = int((cur.fetchone() or {}).get("c") or 0)

        print(f"cn_stock_basics={stocks}")
        print(f"tdx_blocks={blocks}")
        print(f"tdx_block_items={items}")

        if args.stats:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS c FROM tdx_block_items WHERE symbol LIKE %s",
                    ("CN:%",),
                )
                cn_remaining = int((cur.fetchone() or {}).get("c") or 0)
            print(f"tdx_block_items_cn_remaining={cn_remaining}")

        if args.extra:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM tdx_watchlists")
                wl = int((cur.fetchone() or {}).get("c") or 0)
                cur.execute("SELECT COUNT(*) AS c FROM tdx_watchlist_items")
                wli = int((cur.fetchone() or {}).get("c") or 0)
                cur.execute("SELECT COUNT(*) AS c FROM cn_finance_snapshots")
                fin = int((cur.fetchone() or {}).get("c") or 0)
            print(f"tdx_watchlists={wl}")
            print(f"tdx_watchlist_items={wli}")
            print(f"cn_finance_snapshots={fin}")

        sym = str(args.symbol or "").strip()
        if sym:
            norm = SymbolNormalizer.to_db_code(sym, market="CN")
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT block_kind, block_name
                    FROM tdx_block_items
                    WHERE symbol=%s
                    ORDER BY block_kind, block_name
                    LIMIT 50
                    """,
                    (norm,),
                )
                rows = [dict(r) for r in cur.fetchall()]
            print(f"symbol={norm} blocks_sample={len(rows)}")
            for r in rows:
                print(f"- {r.get('block_kind')}\t{r.get('block_name')}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
