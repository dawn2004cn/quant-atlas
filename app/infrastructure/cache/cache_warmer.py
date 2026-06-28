from __future__ import annotations

"""Cache warming service for preloading high-frequency data.

This module implements the cache warming from midify_plan8.md:
- CacheWarmer: Preload core stock data before market open
- Scheduled warming for daily market preparation

Usage:
    warmer = CacheWarmer()
    warmer.warm_market_data()  # Called before market open
"""


from datetime import datetime, time
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class CacheWarmer:
    """Service for warming cache with high-frequency data."""

    def __init__(
        self,
        stock_cache: Any = None,
        redis_client: Any = None,
        core_symbols: list[str] | None = None,
    ):
        self._stock_cache = stock_cache
        self._redis = redis_client
        self._core_symbols = core_symbols or [
            "600519", "000858", "601318", "600036", "000001",
            "600900", "300750", "002594", "601166", "600276",
        ]

    def warm_market_data(self) -> dict[str, Any]:
        """Warm market data cache before trading hours.

        This should be called before market open (9:15 CN time).
        """
        logger.info("Starting market data cache warming...")

        start_time = datetime.now()
        results = {
            "status": "started",
            "symbols_loaded": 0,
            "errors": [],
        }

        try:
            if self._stock_cache:
                all_stocks = self._stock_cache.get_all_stocks(max_age_minutes=5)
                if all_stocks:
                    self._warm_to_redis("market_overview", all_stocks[:100])
                    results["symbols_loaded"] = len(all_stocks)
                    logger.info(f"Warmed {len(all_stocks)} stocks to cache")

            if self._redis:
                self._warm_core_symbols()

            results["status"] = "completed"
            results["duration_seconds"] = (datetime.now() - start_time).total_seconds()

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            results["status"] = "failed"
            results["errors"].append(str(e))

        return results

    def _warm_core_symbols(self) -> None:
        """Warm core symbols to Redis for fast access."""
        if not self._redis or not self._stock_cache:
            return

        for symbol in self._core_symbols:
            try:
                history = self._stock_cache.get_stock_history_for_code(symbol, limit=100)
                if history:
                    key = f"core_history:{symbol}"
                    import json
                    self._redis.setex(key, 3600, json.dumps(history))
            except Exception as e:
                logger.warning(f"Failed to warm {symbol}: {e}")

    def _warm_to_redis(self, key: str, data: Any) -> None:
        """Warm data to Redis."""
        if not self._redis:
            return

        try:
            import json
            serialized = json.dumps(data, default=str)
            self._redis.setex(f"cache:{key}", 300, serialized)
        except Exception as e:
            logger.warning(f"Failed to warm {key}: {e}")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache warming statistics."""
        stats = {
            "core_symbols": len(self._core_symbols),
            "core_symbols_list": self._core_symbols,
        }

        if self._redis:
            try:
                info = self._redis.info("memory")
                stats["redis_memory_used"] = info.get("used_memory_human", "N/A")
            except Exception as e:
                logger.warning("cache_warmer.py.get_cache_stats: %s", e)

        return stats


class MarketOpenScheduler:
    """Scheduler for cache warming before market open."""

    def __init__(self, warmer: CacheWarmer | None = None):
        self._warmer = warmer or CacheWarmer()
        self._last_warm_time: datetime | None = None

    def should_warm(self) -> bool:
        """Check if cache should be warmed."""
        now = datetime.now()

        market_open = time(9, 15)
        current_time = now.time()

        if now.weekday() >= 5:
            return False

        if current_time >= market_open and current_time < time(9, 30):
            if self._last_warm_time is None:
                return True
            if (now - self._last_warm_time).total_seconds() > 3600:
                return True

        return False

    def run_if_needed(self) -> dict[str, Any] | None:
        """Run warming if needed."""
        if self.should_warm():
            result = self._warmer.warm_market_data()
            self._last_warm_time = datetime.now()
            return result
        return None


_global_warmer: CacheWarmer | None = None


def get_cache_warmer() -> CacheWarmer:
    """Get the global cache warmer."""
    global _global_warmer
    if _global_warmer is None:
        from ..database.stock_cache_db import StockCache
        _global_warmer = CacheWarmer(stock_cache=StockCache.default())
    return _global_warmer


def warm_market_data() -> dict[str, Any]:
    """Convenience function to warm market data."""
    return get_cache_warmer().warm_market_data()
