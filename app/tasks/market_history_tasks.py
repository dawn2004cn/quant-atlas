from __future__ import annotations
"""Celery tasks for fetching full market history data."""


from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

from ..celery_app import celery as _celery
from ..domain.enums import MarketCode
from .task_wiring import (
    fetch_crypto_daily,
    fetch_hk_daily,
    fetch_us_daily,
    get_stock_cache,
    to_db_code,
)

from app.core.logger import get_logger

logger = get_logger(__name__)

_MAX_WORKERS = 8

# 港股默认成分股
HK_DEFAULT_SYMBOLS = [
    "0700.HK", "9988.HK", "3690.HK", "1810.HK", "1299.HK",
    "0941.HK", "1398.HK", "3988.HK", "2319.HK", "1044.HK",
    "6630.HK", "9618.HK", "6690.HK", "2382.HK", "0960.HK",
    "0027.HK", "0011.HK", "0001.HK", "0016.HK", "0017.HK",
]

# 美股默认成分股
US_DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "TSLA", "GOOGL", "META", "BRK.B",
    "JPM", "V", "UNH", "XOM", "JNJ", "WMT", "PG", "MA", "CVX",
    "HD", "BAC", "ABBV", "MRK", "PFE", "KO", "PEP", "AVGO", "COST",
]

# 加密货币默认交易对
CRYPTO_DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
]


def _fetch_and_save_history(
    market: MarketCode,
    symbol: str,
    start_date: str,
    end_date: str,
    cache: Any,
) -> dict[str, Any]:
    """获取并保存单只股票历史数据"""
    try:
        if market == MarketCode.HK:
            bars, err = fetch_hk_daily(symbol, start_date, end_date)
        elif market == MarketCode.US:
            bars, err = fetch_us_daily(symbol, start_date, end_date)
        elif market == MarketCode.CRYPTO:
            bars, err = fetch_crypto_daily(symbol, start_date, end_date)
        else:
            return {"ok": False, "symbol": symbol, "error": f"不支持的市场: {market}"}

        if err or not bars:
            return {"ok": False, "symbol": symbol, "error": err or "无数据"}

        db_code = to_db_code(symbol, market.value)
        cache.save_stock_history(db_code, bars)

        return {"ok": True, "symbol": symbol, "db_code": db_code, "count": len(bars)}
    except Exception as e:
        logger.error("Failed to fetch history for %s: %s", symbol, e)
        return {"ok": False, "symbol": symbol, "error": str(e)}


def _fetch_batch(
    market: MarketCode,
    symbols: list[str],
    start_date: str,
    end_date: str,
    cache: Any,
    max_workers: int = _MAX_WORKERS,
) -> list[dict[str, Any]]:
    """并发批量获取并保存股票历史数据."""
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut_map = {
            pool.submit(_fetch_and_save_history, market, sym, start_date, end_date, cache): sym
            for sym in symbols
        }
        for fut in as_completed(fut_map):
            sym = fut_map[fut]
            try:
                result = fut.result()
                results.append(result)
                if result["ok"]:
                    logger.info("Fetched %s history for %s: %d bars", market.value, sym, result.get("count", 0))
                else:
                    logger.warning("Failed to fetch %s history for %s: %s", market.value, sym, result.get("error"))
            except Exception as e:
                logger.error("Unhandled error for %s %s: %s", market.value, sym, e)
                results.append({"ok": False, "symbol": sym, "error": str(e)})
    return results


if _celery is not None:

    @_celery.task(name="app.tasks.market_history_tasks.fetch_hk_history")
    def fetch_hk_history(
        symbols: list[str] | None = None,
        start_date: str = "2010-01-01",
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """获取港股历史数据"""
        from celery import current_task

        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "hk-history")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        symbols = symbols or HK_DEFAULT_SYMBOLS
        cache = get_stock_cache()

        results = _fetch_batch(MarketCode.HK, symbols, start_date, end_date, cache)
        ok_count = sum(1 for r in results if r["ok"])
        return {
            "ok": True,
            "task_id": task_id,
            "market": "HK",
            "total": len(symbols),
            "success": ok_count,
            "failed": len(symbols) - ok_count,
            "results": results,
        }

    @_celery.task(name="app.tasks.market_history_tasks.fetch_us_history")
    def fetch_us_history(
        symbols: list[str] | None = None,
        start_date: str = "2010-01-01",
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """获取美股历史数据"""
        from celery import current_task

        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "us-history")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        symbols = symbols or US_DEFAULT_SYMBOLS
        cache = get_stock_cache()

        results = _fetch_batch(MarketCode.US, symbols, start_date, end_date, cache)
        ok_count = sum(1 for r in results if r["ok"])
        return {
            "ok": True,
            "task_id": task_id,
            "market": "US",
            "total": len(symbols),
            "success": ok_count,
            "failed": len(symbols) - ok_count,
            "results": results,
        }

    @_celery.task(name="app.tasks.market_history_tasks.fetch_crypto_history")
    def fetch_crypto_history(
        symbols: list[str] | None = None,
        start_date: str = "2017-01-01",
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """获取加密货币历史数据"""
        from celery import current_task

        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "crypto-history")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        symbols = symbols or CRYPTO_DEFAULT_SYMBOLS
        cache = get_stock_cache()

        results = _fetch_batch(MarketCode.CRYPTO, symbols, start_date, end_date, cache)
        ok_count = sum(1 for r in results if r["ok"])
        return {
            "ok": True,
            "task_id": task_id,
            "market": "CRYPTO",
            "total": len(symbols),
            "success": ok_count,
            "failed": len(symbols) - ok_count,
            "results": results,
        }

    @_celery.task(name="app.tasks.market_history_tasks.fetch_all_market_history")
    def fetch_all_market_history(
        start_date: str = "2010-01-01",
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """获取所有市场历史数据"""
        from celery import current_task

        req = getattr(current_task, "request", None)
        task_id = str(getattr(req, "id", "") or "all-market-history")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        cache = get_stock_cache()
        all_results: dict[str, Any] = {
            "task_id": task_id,
            "markets": {},
        }

        configs = [
            (MarketCode.HK, HK_DEFAULT_SYMBOLS, start_date),
            (MarketCode.US, US_DEFAULT_SYMBOLS, start_date),
            (MarketCode.CRYPTO, CRYPTO_DEFAULT_SYMBOLS, "2017-01-01"),
        ]

        def _fetch_market(mc: MarketCode, syms: list[str], sd: str) -> dict[str, Any]:
            results = _fetch_batch(mc, syms, sd, end_date, cache)
            ok_count = sum(1 for r in results if r["ok"])
            return {
                "market": mc.value,
                "total": len(syms),
                "success": ok_count,
                "failed": len(syms) - ok_count,
                "results": results,
            }

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            fut_market = {pool.submit(_fetch_market, mc, syms, sd): mc.value for mc, syms, sd in configs}
            for fut in as_completed(fut_market):
                market_name = fut_market[fut]
                try:
                    all_results["markets"][market_name] = fut.result()
                except Exception as e:
                    all_results["markets"][market_name] = {"market": market_name, "total": 0, "success": 0, "failed": 0, "error": str(e)}

        return all_results

else:
    fetch_hk_history = None
    fetch_us_history = None
    fetch_crypto_history = None
    fetch_all_market_history = None
