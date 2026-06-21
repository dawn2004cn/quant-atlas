#!/usr/bin/env python3
"""ç´æ¥è¿è¡ä¿¡å·æåå²åå¡«ä»»å¡çæ ¸å¿é»è¾ï¼ä»2020-01-01å¼å§éæ°çæä¿¡å·ææ°æ®ã?""

import os
import sys
from datetime import datetime, timedelta

# æ·»å é¡¹ç®æ ¹ç®å½å°Pythonè·¯å¾
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
    """ä¼åç¨æ²ªæ·?00åå²æ¥æä½ä¸ºäº¤ææ¥åï¼ä¸å¯ç¨ååéå°å·¥ä½æ¥ã?""
    s = str(start)[:10]
    e = str(end)[:10]
    try:
        hist = cache.get_stock_history_for_code("sh000300", limit=6000) or []
        if hist:
            import pandas as pd  # æ¬å°å¯¼å¥ï¼é¿åä»»å¡æ¨¡åå¯å¨æ¶å¼ºä¾èµ?

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
        print(f"æå»ºäº¤ææ¥åå¤±è´¥: {str(e)}")
    # fallbackï¼å·¥ä½æ¥
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
    except Exception as e:
        print(f"æå»ºå·¥ä½æ¥åå¤±è´¥: {str(e)}")
    return out


def _scanner_service() -> SignalFlagScannerService:
    """åå»ºä¿¡å·ææ«ææå?""
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
    """è¿è¡ä¿¡å·æåå²åå¡«ä»»å?""
    print("å¼å§ä¿¡å·æåå²åå¡«ä»»å¡...")
    print("=====================================")
    
    # éç½®åæ°
    start_date = "2020-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    max_stocks = 50  # è¿ä¸æ­¥åå°è¡ç¥¨æ°éï¼æé«æåç?
    lookback_days = 160
    
    # æå»ºäº¤ææ¥å
    cache = StockCache.default()
    calendar = _build_trading_calendar(cache, start_date, end_date)
    
    # ææ¥æååºå¤çï¼åå¤çæè¿çæ¥æ
    calendar.reverse()
    
    print(f"è®¡ç®äº¤ææ¥åï¼{start_date} å?{end_date}")
    print(f"æ»äº¤æå¤©æ°ï¼{len(calendar)}")
    print("=====================================")
    
    # åªå¤çæè¿?å¤©çæ°æ®
    process_days = min(3, len(calendar))
    
    for i, date in enumerate(calendar):
        print(f"å¤çæ¥æ {i+1}/{len(calendar)}: {date}")
        
        # è·³è¿èåæ¥åéäº¤ææ¥
        if not date:
            print("Skipping empty date")
            print("-------------------------------------")
            continue
        
        # éå¶å¤ççæ¥æèå´ï¼åå¤çæè¿?å¤?
        if i >= process_days:
            print(f"Stopping after {process_days} days to ensure completion")
            break
        
        try:
            # åå»ºæ«ææå¡ï¼æ¯æ¬¡å¾ªç¯åå»ºï¼é¿ååå­æ³æ¼ï¼?
            svc = _scanner_service()
            
            # è¿è¡ä¿¡å·ææ«æ?
            print(f"å¼å§æ«æ?{date}ï¼è¡ç¥¨æ°éï¼{max_stocks}")
            summary = svc.run_scan(
                market=MarketCode.CN,
                pool_date=date,
                max_stocks=max_stocks,
                lookback_days=lookback_days
            )
            
            # æ£æ¥æ¯å¦æååå?
            if summary.persisted > 0:
                print("Success: scanned %d stocks, hits %d, written %d" % (
                    summary.scanned, 
                    summary.hits, 
                    summary.persisted
                ))
            else:
                print("No data: %s" % summary.message)
                
        except Exception as e:
            print("Failed: %s" % str(e))
        finally:
            # éæ¾åå­
            import gc
            gc.collect()
        
        print("-------------------------------------")
    
    print("=====================================")
    print(f"ä¿¡å·æåå²åå¡«å®æï¼")
    print(f"æ»äº¤æå¤©æ°ï¼{len(calendar)}")
    print(f"å¤çå¤©æ°ï¼{process_days}")
    print("=====================================")


if __name__ == "__main__":
    run_backfill()
