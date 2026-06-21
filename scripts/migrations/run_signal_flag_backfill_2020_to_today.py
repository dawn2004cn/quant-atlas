#!/usr/bin/env python3
"""运行信号旗历史回填任务，�?020-01-01到今�?""

import os
import sys
import gc
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.application.services.signal_flag_service import SignalFlagScannerService
from app.domain.enums import MarketCode
from app.infrastructure.database.stock_cache_db import StockCache
from app.infrastructure.repositories.deps import create_signal_flag_pool_repository
from app.application.services.stock_service import StockApplicationService
from app.infrastructure.providers.indicators import TaIndicatorProvider
from app.infrastructure.providers.market_data import MultiSourceMarketProvider
from app.infrastructure.providers.news import AkshareNewsProvider
from app.config import AppSettings


def _build_trading_calendar(cache: StockCache, start: str, end: str) -> list[str]:
    """优先用沪�?00历史日期作为交易日历；不可用则回退到工作日�?""
    s = str(start)[:10]
    e = str(end)[:10]
    try:
        hist = cache.get_stock_history_for_code("sh000300", limit=6000) or []
        if hist:
            import pandas as pd
            df = pd.DataFrame(hist)
            col = None
            for c in df.columns:
                if str(c).lower() == "date":
                    col = c
                    break
            if col is None:
                col = "date" if "date" in df.columns else df.columns[0]
            ds = pd.to_datetime(df[col], errors="coerce").dt.date.astype(str)
            ds = [x for x in ds.tolist() if x and s <= x <= e]
            ds = sorted(list(dict.fromkeys(ds)))
            if ds:
                return ds
    except Exception as e:
        logger.warning("run_signal_flag_backfill_2020_to_today.parse_date_range: %s", e)
    from datetime import timedelta
    out: list[str] = []
    try:
        d0 = datetime.strptime(s, "%Y-%m-%d")
        d1 = datetime.strptime(e, "%Y-%m-%d")
        cur = d0
        while cur <= d1:
            wd = cur.weekday()
            if wd < 5:
                out.append(cur.strftime("%Y-%m-%d"))
            cur = cur + timedelta(days=1)
    except Exception:
        return []
    return out


def _scanner_service() -> SignalFlagScannerService:
    settings = AppSettings.from_env()
    mp = MultiSourceMarketProvider()
    stock_service = StockApplicationService(mp, TaIndicatorProvider(), AkshareNewsProvider())
    repo = create_signal_flag_pool_repository(settings)
    return SignalFlagScannerService(
        stock_service=stock_service,
        stock_cache=StockCache.default(),
        repository=repo,
        enable_qlib=settings.enable_qlib,
    )


def run_backfill():
    print("=" * 60)
    print("信号旗历史回填任�?)
    print("=" * 60)

    start_date = "2020-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    max_stocks = 100
    lookback_days = 160
    limit_days = 30  # 限制只处理最�?0个交易日

    print(f"开始日�? {start_date}")
    print(f"结束日期: {end_date}")
    print(f"股票数量: {max_stocks}")
    print(f"回溯天数: {lookback_days}")
    print(f"限制处理天数: {limit_days} (最近交易日)")
    print("=" * 60)

    cache = StockCache.default()
    calendar = _build_trading_calendar(cache, start_date, end_date)

    # 按日期倒序，只取最近的limit_days�?    calendar = sorted(calendar, reverse=True)[:limit_days]

    print(f"计算交易日历完成，待处理天数: {len(calendar)}")
    print("=" * 60)

    total_written = 0
    total_failed = 0
    total_days = len(calendar)

    for i, date in enumerate(calendar):
        print(f"[{i+1}/{total_days}] 处理日期: {date}", end=" ... ")

        try:
            svc = _scanner_service()
            summary = svc.run_scan(
                market=MarketCode.CN,
                pool_date=date,
                max_stocks=max_stocks,
                lookback_days=lookback_days
            )

            if summary.persisted > 0:
                print(f"成功 (扫描{summary.scanned}�? 命中{summary.hits}�? 写入{summary.persisted}�?")
                total_written += 1
            else:
                print(f"无数�?)
                total_failed += 1

        except Exception as e:
            print(f"失败: {str(e)[:50]}")
            total_failed += 1
        finally:
            del svc
            gc.collect()

    print("=" * 60)
    print(f"回填完成!")
    print(f"总交易天�? {total_days}")
    print(f"成功写入: {total_written} �?)
    print(f"无数�?失败: {total_failed} �?)
    print(f"完成�? {total_written/total_days*100:.2f}%")
    print("=" * 60)


if __name__ == "__main__":
    run_backfill()
