#!/usr/bin/env python3
"""清空 instance 中 SQLite 的日 K 缓存，便于从 TDX 重新拉取并写入。

用法:
  python scripts/refresh_stock_history_cache.py              # 清空全部 stock_history
  python scripts/refresh_stock_history_cache.py --code CN:600519  # 仅清空指定标的
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys


def _default_db_path() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(root, "instance", "stock_cache.db")


def main() -> int:
    parser = argparse.ArgumentParser(description="清空 stock_history 表以便重新导入 K 线")
    parser.add_argument(
        "--code",
        help="仅删除该缓存键，例如 CN:600519（与 stock_history.stock_code 一致）",
    )
    parser.add_argument("--db", help="stock_cache.db 路径", default=_default_db_path())
    args = parser.parse_args()
    db_path = args.db
    if not os.path.isfile(db_path):
        print(f"数据库不存在: {db_path}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(db_path)
    try:
        if args.code:
            cur = conn.execute("DELETE FROM stock_history WHERE stock_code = ?", (args.code,))
            print(f"已删除 {cur.rowcount} 行 (stock_code={args.code})")
        else:
            cur = conn.execute("DELETE FROM stock_history")
            print(f"已清空 stock_history，共删除 {cur.rowcount} 行")
        conn.commit()
    finally:
        conn.close()
    print("下次请求个股历史 K 时将尝试从通达信拉取并回写缓存。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
