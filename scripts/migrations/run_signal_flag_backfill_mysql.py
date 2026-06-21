#!/usr/bin/env python3
"""运行信号旗历史回填任务 - 简化版，直接从MySQL读取"""

import os, sys, gc
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.domain.enums import MarketCode
from app.infrastructure.database.stock_cache_db import StockCache
from app.infrastructure.repositories.deps import create_signal_flag_pool_repository
from app.config import AppSettings


def _build_trading_calendar(start: str, end: str) -> list[str]:
    s, e = start[:10], end[:10]
    try:
        cache = StockCache.default()
        rows = cache.get_stock_history_for_code('sh000300', limit=6000)
        if rows:
            dates = sorted(set(str(r['date'])[:10] for r in rows if r.get('date')))
            return [d for d in dates if s <= d <= e]
    except Exception:
        pass
    from datetime import timedelta
    out = []
    try:
        d0, d1 = datetime.strptime(s, "%Y-%m-%d"), datetime.strptime(e, "%Y-%m-%d")
        cur = d0
        while cur <= d1:
            if cur.weekday() < 5:
                out.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
    except Exception as e:
        logger.warning("run_signal_flag_backfill_mysql.backfill: %s", e)
    return out


def run_scan_for_date(date: str, max_stocks: int = 100, lookback_days: int = 160) -> dict:
    from app.application.services.signal_flag_service import SignalFlagScannerService
    from app.application.services.stock_service import StockApplicationService
    from app.infrastructure.providers.indicators import TaIndicatorProvider
    from app.infrastructure.providers.market_data import MultiSourceMarketProvider
    from app.infrastructure.providers.news import AkshareNewsProvider

    settings = AppSettings.from_env()
    mp = MultiSourceMarketProvider()
    stock_service = StockApplicationService(mp, TaIndicatorProvider(), AkshareNewsProvider())
    repo = create_signal_flag_pool_repository(settings)
    svc = SignalFlagScannerService(
        stock_service=stock_service,
        stock_cache=StockCache.default(),
        repository=repo,
        enable_qlib=settings.enable_qlib,
    )
    return svc.run_scan(market=MarketCode.CN, pool_date=date, max_stocks=max_stocks, lookback_days=lookback_days)


def main():
    print("=" * 60)
    print("Signal Flag Backfill (MySQL Mode)")
    print("=" * 60)

    start_date, end_date = "2020-01-01", datetime.now().strftime("%Y-%m-%d")
    max_stocks, lookback_days, limit_days = 100, 160, 30

    print(f"Period: {start_date} to {end_date}")
    print(f"Stocks: {max_stocks}, Lookback: {lookback_days}, Limit: {limit_days} days")
    print("=" * 60)

    calendar = _build_trading_calendar(start_date, end_date)
    calendar = sorted(set(calendar), reverse=True)[:limit_days]

    print(f"Trading days to process: {len(calendar)}")
    print("=" * 60)

    written, failed = 0, 0
    for i, date in enumerate(calendar):
        print(f"[{i+1}/{len(calendar)}] {date}", end=" ... ", flush=True)
        try:
            result = run_scan_for_date(date, max_stocks, lookback_days)
            if result.persisted > 0:
                print(f"OK (scan={result.scanned}, hit={result.hits}, write={result.persisted})")
                written += 1
            else:
                print("EMPTY")
                failed += 1
        except Exception as e:
            print(f"FAIL: {str(e)[:40]}")
            failed += 1
        gc.collect()

    print("=" * 60)
    print(f"Done! Success: {written}, Failed/Empty: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
