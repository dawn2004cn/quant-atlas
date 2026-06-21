#!/usr/bin/env python3
"""统一所有 A 股股票代码为 sh600519 格式（可重复执行）。

处理策略：
1. 每个表使用独立连接，避免一个表超时影响其他表
2. 对大表使用直接 UPDATE，避免 DISTINCT 超时
3. 对小表使用 DISTINCT 查询后批量更新
4. 纯 6 位数字 → 根据规则添加 sh/sz/bj 前缀
5. CN: / cn: 前缀 → 移除

用法（项目根目录）:
  python scripts/migrations/unify_all_stock_codes.py --dry-run
  python scripts/migrations/unify_all_stock_codes.py --apply
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


# ============================================================
# 大表（使用直接 UPDATE，避免 DISTINCT 超时）
# ============================================================
LARGE_TABLES = [
    ("stock_history", "stock_code"),
    ("stock_history_sh", "stock_code"),
    ("stock_history_sz", "stock_code"),
    ("stock_history_bj", "stock_code"),
]

# ============================================================
# 小表（使用 DISTINCT 查询后批量更新）
# ============================================================
SMALL_TABLES = [
    # 自选股
    ("watchlist", "symbol"),
    ("stock_group_items", "symbol"),
    ("tdx_block_items", "symbol"),
    ("tdx_watchlist_items", "symbol"),
    # 股票基本信息
    ("stocks", "code"),
    ("cn_stock_basics", "symbol"),
    # 财务 / 研报 / 新闻
    ("cn_finance_snapshots", "symbol"),
    ("yanbao_items", "stock_code"),
    ("archived_news", "symbol"),
    ("news_symbol_meta", "symbol"),
    # 信号 / 预测
    ("signal_flag_pool", "code"),
    ("fingpt_predictions", "ticker"),
    ("fingpt_sentiment", "ticker"),
    ("kronos_predictions", "symbol"),
    # 投研 / 经理
    ("analysis_reports", "symbol"),
    ("manager_trades", "symbol"),
    ("manager_positions_state", "symbol"),
    ("manager_holdings_snap", "symbol"),
    # 龙虎榜
    ("longhu_daily", "code"),
    # AI 委员会
    ("ai_trading_records", "symbol"),
    ("ai_committee_selection_trades", "symbol"),
    # 板块成分
    ("em_hot_sector_members", "symbol"),
    # 用户竞赛
    ("user_race_trades", "symbol"),
    # 执行记录
    ("execution_records", "symbol"),
]


def _migrate_large_table(table: str, column: str, apply: bool) -> dict:
    """迁移大表：使用直接 UPDATE，避免 DISTINCT 超时。"""
    stats = {"updated": 0, "error": None}

    settings = AppSettings.from_env()
    conn = mysql_connect(settings.mysql)
    if not conn:
        stats["error"] = "Connection failed"
        return stats

    try:
        with conn.cursor() as cur:
            # 检查表是否存在
            cur.execute("SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s", (table,))
            row = cur.fetchone()
            cnt = row[0] if isinstance(row, tuple) else (row.get("cnt") or row.get("CNT"))
            if not cnt:
                return stats

            # 检查列是否存在
            cur.execute("SELECT COUNT(*) AS cnt FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s", (table, column))
            row = cur.fetchone()
            cnt = row[0] if isinstance(row, tuple) else (row.get("cnt") or row.get("CNT"))
            if not cnt:
                return stats

            if apply:
                # 直接 UPDATE CN: 前缀
                cur.execute(
                    f"UPDATE {table} SET {column} = SUBSTRING({column}, 4) "
                    f"WHERE {column} LIKE 'CN:%' OR {column} LIKE 'cn:%'"
                )
                stats["updated"] += cur.rowcount

                # 直接 UPDATE 纯 6 位数字（需要根据规则添加前缀）
                # 6xxxxx → sh6xxxxx
                cur.execute(
                    f"UPDATE {table} SET {column} = CONCAT('sh', {column}) "
                    f"WHERE {column} REGEXP '^6[0-9]{{5}}$'"
                )
                stats["updated"] += cur.rowcount

                # 0xxxxx, 3xxxxx → sz0xxxxx, sz3xxxxx
                cur.execute(
                    f"UPDATE {table} SET {column} = CONCAT('sz', {column}) "
                    f"WHERE {column} REGEXP '^[03][0-9]{{5}}$'"
                )
                stats["updated"] += cur.rowcount

                # 8xxxxx, 4xxxxx → bj8xxxxx, bj4xxxxx
                cur.execute(
                    f"UPDATE {table} SET {column} = CONCAT('bj', {column}) "
                    f"WHERE {column} REGEXP '^[84][0-9]{{5}}$'"
                )
                stats["updated"] += cur.rowcount

                conn.commit()
            else:
                # DRY RUN: 估算影响行数
                cur.execute(
                    f"SELECT COUNT(*) AS cnt FROM {table} "
                    f"WHERE {column} LIKE 'CN:%' OR {column} LIKE 'cn:%' "
                    f"OR {column} REGEXP '^[0-9]{{6}}$'"
                )
                row = cur.fetchone()
                stats["updated"] = row[0] if isinstance(row, tuple) else (row.get("cnt") or row.get("CNT"))

    except Exception as exc:
        stats["error"] = str(exc)
    finally:
        conn.close()

    return stats


def _migrate_small_table(table: str, column: str, apply: bool) -> dict:
    """迁移小表：使用 DISTINCT 查询后批量更新。"""
    stats = {"to_update": 0, "updated": 0, "error": None}

    settings = AppSettings.from_env()
    conn = mysql_connect(settings.mysql)
    if not conn:
        stats["error"] = "Connection failed"
        return stats

    try:
        with conn.cursor() as cur:
            # 检查表是否存在
            cur.execute("SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s", (table,))
            row = cur.fetchone()
            cnt = row[0] if isinstance(row, tuple) else (row.get("cnt") or row.get("CNT"))
            if not cnt:
                return stats

            # 检查列是否存在
            cur.execute("SELECT COUNT(*) AS cnt FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s", (table, column))
            row = cur.fetchone()
            cnt = row[0] if isinstance(row, tuple) else (row.get("cnt") or row.get("CNT"))
            if not cnt:
                return stats

            # 查找需要更新的记录
            cur.execute(
                f"SELECT DISTINCT {column} FROM {table} "
                f"WHERE {column} LIKE %s OR {column} LIKE %s OR {column} REGEXP %s",
                ("CN:%", "cn:%", "^[0-9]{6}$"),
            )
            rows = cur.fetchall()

            to_update = []
            for row in rows:
                old = row[0] if isinstance(row, tuple) else (row.get(column) or row.get(column.upper()))
                if not old:
                    continue
                # 判断是否需要迁移
                if old.lower().startswith("cn:") or (old.isdigit() and len(old) == 6):
                    new = SymbolNormalizer.to_db_code(old)
                    if new != old:
                        to_update.append((old, new))

            stats["to_update"] = len(to_update)

            if apply and to_update:
                for old, new in to_update:
                    cur.execute(
                        f"UPDATE {table} SET {column}=%s WHERE {column}=%s",
                        (new, old),
                    )
                    stats["updated"] += cur.rowcount
                conn.commit()

    except Exception as exc:
        stats["error"] = str(exc)
    finally:
        conn.close()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="统一所有 A 股股票代码为 sh600519 格式")
    parser.add_argument("--apply", action="store_true", help="写入数据库（默认仅预览）")
    parser.add_argument("--dry-run", action="store_true", help="仅统计（默认）")
    parser.add_argument("--tables", nargs="*", help="指定要迁移的表名（默认全部）")
    args = parser.parse_args()
    apply = bool(args.apply)
    if not apply:
        print("=" * 60)
        print("DRY RUN — 加 --apply 才会写入数据库")
        print("=" * 60)

    settings = AppSettings.from_env()
    if not settings.use_mysql or settings.mysql is None:
        print("MySQL 未启用，跳过")
        return 1

    # 确定要迁移的表
    all_tables = LARGE_TABLES + SMALL_TABLES
    if args.tables:
        all_tables = [(t, c) for t, c in all_tables if t in args.tables]

    grand_total = 0
    for table, col in all_tables:
        try:
            # 大表使用直接 UPDATE，小表使用 DISTINCT
            if (table, col) in LARGE_TABLES:
                stats = _migrate_large_table(table, col, apply=apply)
            else:
                stats = _migrate_small_table(table, col, apply=apply)

            if stats["error"]:
                print(f"  {table}.{col}: ERROR ({stats['error']})")
                continue
            # 在 apply 模式下使用 updated，在 dry-run 模式下使用 to_update
            upd = stats.get("updated", 0) if apply else stats.get("to_update", stats.get("updated", 0))
            if upd > 0:
                print(f"  {table}.{col}: 更新 {upd} 条")
            grand_total += upd
        except Exception as exc:
            print(f"  {table}.{col}: skip ({exc})")

    if apply:
        print(f"\n{'=' * 60}")
        print(f"COMMITTED — 共处理 ~{grand_total} 条记录")
        print(f"{'=' * 60}")
    else:
        print(f"\n{'=' * 60}")
        print(f"DRY RUN — 将影响 ~{grand_total} 条记录")
        print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
