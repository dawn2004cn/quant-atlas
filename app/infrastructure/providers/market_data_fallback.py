from __future__ import annotations
"""Market data fallback strategy - implements Chain of Responsibility pattern.

This module provides resilient data fetching with automatic fallbacks:
1. RealtimeProvider (primary)
2. CacheProvider (fallback 1)
3. IndicatorReconstructor (fallback 2 - reconstruct from historical data)

Following Strategy Pattern for flexible provider switching.
"""


import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ...domain.enums import MarketCode

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DataSourceInfo:
    """Metadata about data source."""
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    age_seconds: float = 0
    is_fallback: bool = False


@dataclass
class FallbackResult:
    """Result with data source metadata."""
    data: Any
    source_info: DataSourceInfo
    success: bool
    error_message: str | None = None


class MarketDataSource(ABC):
    """Abstract base for market data sources."""

    @abstractmethod
    def get_quotes(self, symbols: list[str], market: MarketCode) -> list[dict[str, Any]]:
        """Get real-time quotes."""
        raise NotImplementedError

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Get historical OHLCV data."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this data source is currently available."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Data source name for logging."""
        raise NotImplementedError


class RealtimeProvider(MarketDataSource):
    """Primary real-time market data provider."""

    def __init__(self, primary_provider: Any):
        self._provider = primary_provider

    @property
    def name(self) -> str:
        return "RealtimeProvider"

    def is_available(self) -> bool:
        try:
            return self._provider is not None
        except Exception:
            return False

    def get_quotes(self, symbols: list[str], market: MarketCode) -> list[dict[str, Any]]:
        try:
            return self._provider.get_realtime_quotes(symbols, market)
        except Exception as e:
            logger.warning(f"RealtimeProvider quotes failed: {e}")
            raise

    def get_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        try:
            return self._provider.get_stock_history(symbol, market, start, end)
        except Exception as e:
            logger.warning(f"RealtimeProvider history failed: {e}")
            raise


class CacheProvider(MarketDataSource):
    """Fallback to local cache when real-time fails."""

    def __init__(self, stock_cache: Any):
        self._cache = stock_cache

    @property
    def name(self) -> str:
        return "CacheProvider"

    def is_available(self) -> bool:
        try:
            return self._cache is not None
        except Exception:
            return False

    def get_quotes(self, symbols: list[str], market: MarketCode) -> list[dict[str, Any]]:
        try:
            all_stocks = self._cache.get_all_stocks(max_age_minutes=1440)
            if not all_stocks:
                raise ValueError("No cached stock data available")

            symbol_set = set(symbols) if symbols else None
            result = [
                s for s in all_stocks
                if symbol_set is None or s.get("code") in symbol_set
            ]
            return result
        except Exception as e:
            logger.warning(f"CacheProvider quotes failed: {e}")
            raise

    def get_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        try:
            return self._cache.get_stock_history(symbol, start, end)
        except Exception as e:
            logger.warning(f"CacheProvider history failed: {e}")
            raise


class IndicatorReconstructor(MarketDataSource):
    """Fallback to reconstruct data from indicators/history.

    This is a last-resort fallback that reconstructs missing data
    from available historical indicators.
    """

    def __init__(self, indicator_provider: Any = None, stock_cache: Any = None):
        self._indicator_provider = indicator_provider
        self._cache = stock_cache

    @property
    def name(self) -> str:
        return "IndicatorReconstructor"

    def is_available(self) -> bool:
        return self._cache is not None

    def get_quotes(self, symbols: list[str], market: MarketCode) -> list[dict[str, Any]]:
        if not symbols:
            return []

        history_data = []
        for symbol in symbols:
            try:
                hist = self._cache.get_stock_history_for_code(symbol, limit=1)
                if hist:
                    latest = hist[-1]
                    history_data.append({
                        "code": symbol,
                        "price": latest.get("close", 0),
                        "open": latest.get("open", 0),
                        "high": latest.get("high", 0),
                        "low": latest.get("low", 0),
                        "close": latest.get("close", 0),
                        "volume": latest.get("volume", 0),
                        "date": latest.get("date", ""),
                    })
            except Exception as e:
                logger.debug(f"IndicatorReconstructor failed for {symbol}: {e}")

        return history_data

    def get_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        try:
            return self._cache.get_stock_history(symbol, start, end)
        except Exception as e:
            logger.warning(f"IndicatorReconstructor history failed: {e}")
            return []


class MarketDataChain:
    """Chain of Responsibility for market data with automatic fallback.

    Usage:
        chain = MarketDataChain(realtime_provider, stock_cache, indicator_provider)
        result = chain.get_quotes(["600519"], MarketCode.CN)
        print(f"Data from: {result.source_info.source}")
    """

    def __init__(
        self,
        primary_provider: Any,
        stock_cache: Any = None,
        indicator_provider: Any = None,
    ):
        self._sources: list[MarketDataSource] = []

        if primary_provider:
            self._sources.append(RealtimeProvider(primary_provider))

        if stock_cache:
            self._sources.append(CacheProvider(stock_cache))

        if indicator_provider or stock_cache:
            self._sources.append(IndicatorReconstructor(indicator_provider, stock_cache))

    def get_quotes(self, symbols: list[str], market: MarketCode) -> FallbackResult:
        """Get quotes with automatic fallback."""
        return self._fetch_with_fallback(
            lambda source: source.get_quotes(symbols, market),
            "quotes"
        )

    def get_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> FallbackResult:
        """Get history with automatic fallback."""
        return self._fetch_with_fallback(
            lambda source: source.get_history(symbol, market, start, end),
            "history"
        )

    def _fetch_with_fallback(
        self,
        fetch_func: callable,
        data_type: str,
    ) -> FallbackResult:
        """Execute fetch with automatic fallback through the chain."""
        last_error = None

        for idx, source in enumerate(self._sources):
            if not source.is_available():
                logger.debug(f"Source {source.name} not available, skipping")
                continue

            try:
                data = fetch_func(source)
                if data:
                    return FallbackResult(
                        data=data,
                        source_info=DataSourceInfo(
                            source=source.name,
                            is_fallback=(idx > 0),
                        ),
                        success=True,
                    )
            except Exception as e:
                last_error = e
                logger.warning(f"{source.name} failed for {data_type}: {e}")
                continue

        return FallbackResult(
            data=None,
            source_info=DataSourceInfo(
                source="None",
                is_fallback=True,
            ),
            success=False,
            error_message=str(last_error) if last_error else "All sources failed",
        )

    @property
    def sources(self) -> list[str]:
        """Get list of available source names."""
        return [s.name for s in self._sources if s.is_available()]


class RedisCacheFacade:
    """Redis-backed cache facade for high-frequency DTO caching.

    Provides L1 cache layer for frequently accessed data like MarketOverviewDTO.
    """

    def __init__(self, redis_url: str | None = None):
        self._redis = None
        self._redis_url = redis_url
        self._enabled = redis_url is not None

    def _get_redis(self):
        if not self._enabled:
            return None

        if self._redis is None:
            try:
                from app.infrastructure.redis_client import RedisClientPool
                self._redis = RedisClientPool.get(self._redis_url).client
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._enabled = False
                return None
        return self._redis

    def get(self, key: str) -> Any | None:
        """Get cached value."""
        r = self._get_redis()
        if not r:
            return None
        try:
            import json
            data = r.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.debug(f"Redis get failed: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set cached value with TTL."""
        r = self._get_redis()
        if not r:
            return False
        try:
            import json
            r.setex(key, ttl_seconds, json.dumps(value))
            return True
        except Exception as e:
            logger.debug(f"Redis set failed: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete cached value."""
        r = self._get_redis()
        if not r:
            return False
        try:
            r.delete(key)
            return True
        except Exception:
            return False

    @property
    def is_enabled(self) -> bool:
        return self._enabled


def create_market_data_chain(
    market_provider: Any,
    stock_cache: Any = None,
    indicator_provider: Any = None,
    redis_url: str | None = None,
) -> tuple[MarketDataChain, RedisCacheFacade]:
    """Factory function to create market data chain with Redis cache.

    Returns:
        tuple: (MarketDataChain, RedisCacheFacade)
    """
    chain = MarketDataChain(market_provider, stock_cache, indicator_provider)
    redis_cache = RedisCacheFacade(redis_url)
    return chain, redis_cache