#!/usr/bin/env python3
"""运行信号旗历史回填任�?- 强制使用MySQL存储"""

import os, sys, gc
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 强制使用MySQL
os.environ['DATABASE_BACKEND'] = 'mysql'
os.environ.setdefault('MYSQL_HOST', '192.168.8.103')
os.environ.setdefault('MYSQL_PORT', '3307')
os.environ.setdefault('MYSQL_USER', 'admin')
os.environ.setdefault('MYSQL_PASSWORD', "")
os.environ.setdefault('MYSQL_DATABASE', 'a_stock_monitor')

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
        logger.warning("run_signal_flag_backfill_mysql_2020.backfill: %s", e)
    return out


def run_scan_for_date(date: str, max_stocks: int = 100, lookback_days: int = 160) -> dict:
    from app.application.services.signal_flag_service import SignalFlagScannerService
    from app.application.services.stock_service import StockApplicationService
    from app.infrastructure.providers.indicators import TaIndicatorProvider
    from app.infrastructure.providers.market_data import MultiSourceMarketProvider
    from app.infrastructure.providers.news import AkshareNewsProvider

    settings = AppSettings.from_env()
    print(f"DEBUG: use_mysql={settings.use_mysql}, mysql={settings.mysql}")
    
    mp = MultiSourceMarketProvider()
    stock_service = StockApplicationService(mp, TaIndicatorProvider(), AkshareNewsProvider())
    repo = create_signal_flag_pool_repository(settings)
    
    # 检查是否使用MySQL
    print(f"DEBUG: Repository using MySQL: {hasattr(repo, '_is_mysql') and repo._is_mysql}")
    
    svc = SignalFlagScannerService(
        stock_service=stock_service,
        stock_cache=StockCache.default(),
        repository=repo,
        enable_qlib=settings.enable_qlib,
    )
    return svc.run_scan(market=MarketCode.CN, pool_date=date, max_stocks=max_stocks, lookback_days=lookback_days)


def main():
    print("=" * 60)
    print("Signal Flag Backfill (MySQL Mode) - 2020-01-01 to Today")
    print("=" * 60)

    start_date, end_date = "2020-01-01", datetime.now().strftime("%Y-%m-%d")
    max_stocks, lookback_days, limit_days = 100, 160, 30

    print(f"Period: {start_date} to {end_date}")
    print(f"Stocks: {max_stocks}, Lookback: {lookback_days}, Limit: {limit_days} days")
    print("Storage: MySQL (192.168.8.103:3307/a_stock_monitor)")
    print("=" * 60)

    calendar = _build_trading_calendar(start_date, end_date)
    
    # 按日期正序，�?020年开始处�?    calendar = sorted(set(calendar))
    
    # 限制处理天数，避免任务过�?    total_days = len(calendar)
    calendar = calendar[:limit_days]

    print(f"Total trading days: {total_days}")
    print(f"Processing first {len(calendar)} days (2020-01-01 onwards)")
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
