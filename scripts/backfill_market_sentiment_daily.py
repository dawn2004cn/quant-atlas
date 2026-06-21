#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 ``stock_history`` 按交易日聚合全市场涨跌家数，写入 ``market_sentiment_daily``。

逻辑（与行情轮询写入的口径一致：上涨家数 / 总有效家数 → 0~100 分由回测侧读取）：
按日期升序遍历；对每只标的若存在「上一根已处理 bar」的收盘价，则与当日收盘比较，
统计涨 / 跌 / 平（平：相对变化绝对值 < 阈值）；无上一根则不计入当日分母（首 bar 仅更新状态）。

用法::

  python scripts/backfill_market_sentiment_daily.py
  python scripts/backfill_market_sentiment_daily.py --start 2020-01-01 --end 2024-12-31
  python scripts/backfill_market_sentiment_daily.py --dry-run

依赖：与 Web 相同的环境变量 / ``config/config.cfg``（``DATABASE_BACKEND``、MySQL 等），使用 ``StockCache.default()``。
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.infrastructure.database.stock_cache_db import StockCache


def _safe_close(x: float) -> bool:
    return math.isfinite(x) and x > 0


def run_backfill(
    *,
    market: str,
    start: str,
    end: str,
    flat_rel_eps: float,
    dry_run: bool,
    min_total: int,
    progress_every: int,
) -> dict[str, int]:
    cache = StockCache.default()
    dates = cache.list_distinct_stock_history_dates(start, end)
    prev_close: dict[str, float] = {}
    written = 0
    skipped = 0
    for i, d in enumerate(dates):
        rows = cache.fetch_stock_history_closes_on_date(d)
        up = down = flat = 0
        for code, c in rows:
            if not code or not _safe_close(c):
                continue
            p = prev_close.get(code)
            if p is None or not _safe_close(p):
                continue
            rel = (c - p) / p
            if abs(rel) < flat_rel_eps:
                flat += 1
            elif c > p:
                up += 1
            else:
                down += 1
        total = up + down + flat
        if total < min_total:
            skipped += 1
        else:
            if not dry_run:
                cache.save_sentiment_daily(market, d, up, down, flat)
            written += 1
        for code, c in rows:
            if code and _safe_close(c):
                prev_close[code] = c
        if progress_every > 0 and (i + 1) % progress_every == 0:
            print(f"  … {i + 1}/{len(dates)} 日 ({d}) up={up} down={down} flat={flat} total={total}", flush=True)
    return {"dates": len(dates), "written": written, "skipped_low_coverage": skipped}


def main() -> int:
    p = argparse.ArgumentParser(description="从 stock_history 回填 market_sentiment_daily")
    p.add_argument("--start", help="起始日 YYYY-MM-DD（默认取库内最小日）")
    p.add_argument("--end", help="结束日 YYYY-MM-DD（默认取库内最大日）")
    p.add_argument("--market", default="CN", help="市场键，写入 market_sentiment_daily.market")
    p.add_argument(
        "--flat-eps",
        type=float,
        default=1e-6,
        help="视为平盘的相对涨跌幅绝对值阈值（默认 1e-6）",
    )
    p.add_argument(
        "--min-total",
        type=int,
        default=30,
        help="当日有效涨跌样本少于该数则跳过写入（默认 30，避免极稀疏日）",
    )
    p.add_argument("--dry-run", action="store_true", help="只统计不写库")
    p.add_argument("--progress-every", type=int, default=50, help="每 N 个交易日打印一行，0 关闭")
    args = p.parse_args()

    cache = StockCache.default()
    mn, mx = cache.get_stock_history_date_bounds()
    if not mn or not mx:
        print("stock_history 无数据，退出。", file=sys.stderr)
        return 1
    start = (args.start or mn).strip()[:10]
    end = (args.end or mx).strip()[:10]
    if start > end:
        print("start > end", file=sys.stderr)
        return 1

    print(f"区间: {start} ~ {end}  market={args.market}  dry_run={args.dry_run}")
    stats = run_backfill(
        market=args.market.strip() or "CN",
        start=start,
        end=end,
        flat_rel_eps=max(0.0, float(args.flat_eps)),
        dry_run=bool(args.dry_run),
        min_total=max(0, int(args.min_total)),
        progress_every=max(0, int(args.progress_every)),
    )
    print(
        "完成: 交易日数=%(dates)s  写入行=%(written)s  跳过(样本过少)=%(skipped_low_coverage)s"
        % stats
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
