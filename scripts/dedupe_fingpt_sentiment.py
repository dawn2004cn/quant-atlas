"""Deduplicate `fingpt_sentiment` by (ticker, summary_hash) in MySQL.

Examples:
  python scripts/dedupe_fingpt_sentiment.py --dry-run
  python scripts/dedupe_fingpt_sentiment.py --apply
  python scripts/dedupe_fingpt_sentiment.py --apply --ticker sh600519
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="Actually delete duplicates (default: dry-run).")
    p.add_argument("--dry-run", action="store_true", help="Preview duplicates without deleting.")
    p.add_argument("--ticker", default="", help="Optional: only dedupe a single ticker.")
    p.add_argument("--sample", type=int, default=20, help="Print top N duplicate groups.")
    args = p.parse_args()

    s = AppSettings.from_env()
    if not s.use_mysql or s.mysql is None:
        print("mysql_not_enabled")
        return 2

    do_apply = bool(args.apply) and not bool(args.dry_run)
    ticker = (args.ticker or "").strip() or None
    sample = max(0, min(int(args.sample or 20), 200))

    conn = mysql_connect(s.mysql)
    try:
        # Ensure summary_hash is populated (safe to run multiple times)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE fingpt_sentiment "
                "SET summary_hash = SHA2(COALESCE(summary, ''), 256) "
                "WHERE summary_hash IS NULL OR summary_hash = ''"
            )
        conn.commit()

        # Count duplicate groups
        where = "WHERE ticker = %s" if ticker else ""
        params = (ticker,) if ticker else ()
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT COUNT(*) AS dup_groups
                FROM (
                    SELECT ticker, summary_hash
                    FROM fingpt_sentiment
                    {where}
                    GROUP BY ticker, summary_hash
                    HAVING COUNT(*) > 1
                ) t
                """,
                params,
            )
            dup_groups = int((cur.fetchone() or {}).get("dup_groups") or 0)
        print(f"duplicate_groups={dup_groups}")

        if sample > 0 and dup_groups > 0:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT ticker, summary_hash, COUNT(*) AS c, MAX(id) AS keep_id
                    FROM fingpt_sentiment
                    {where}
                    GROUP BY ticker, summary_hash
                    HAVING COUNT(*) > 1
                    ORDER BY c DESC, keep_id DESC
                    LIMIT %s
                    """,
                    (*params, sample),
                )
                rows = cur.fetchall() or []
            for r in rows:
                print(
                    f"- ticker={r.get('ticker')} c={r.get('c')} keep_id={r.get('keep_id')} "
                    f"hash={str(r.get('summary_hash') or '')[:12]}鈥?
                )

        if not do_apply:
            print("mode=dry_run")
            return 0

        # Delete duplicates: keep MAX(id) per (ticker, summary_hash)
        join_where = "AND fs.ticker = %s" if ticker else ""
        join_params = (ticker,) if ticker else ()
        with conn.cursor() as cur:
            cur.execute(
                f"""
                DELETE fs
                FROM fingpt_sentiment fs
                JOIN (
                    SELECT ticker, summary_hash, MAX(id) AS keep_id, COUNT(*) AS c
                    FROM fingpt_sentiment
                    {where}
                    GROUP BY ticker, summary_hash
                    HAVING c > 1
                ) d
                  ON fs.ticker = d.ticker
                 AND fs.summary_hash = d.summary_hash
                 AND fs.id <> d.keep_id
                {join_where}
                """,
                (*join_params, *join_params),
            )
            deleted = int(cur.rowcount or 0)
        conn.commit()
        print(f"deleted_rows={deleted}")

        # Try to add unique index (if it was skipped before). Ignore duplicates/key-exists.
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "ALTER TABLE fingpt_sentiment "
                    "ADD UNIQUE KEY ux_fingpt_sent_ticker_hash (ticker, summary_hash)"
                )
            conn.commit()
            print("unique_index_added=1")
        except Exception as exc:  # noqa: BLE001
            print(f"unique_index_added=0 err={exc}")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

