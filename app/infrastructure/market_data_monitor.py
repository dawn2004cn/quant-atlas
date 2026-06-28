from __future__ import annotations
"""Real-time market data subscription and freshness monitoring."""


from dataclasses import dataclass
from datetime import datetime
from typing import Any
from collections.abc import Callable
from enum import Enum

from app.core.logger import get_logger

logger = get_logger(__name__)


class DataFreshness(Enum):
    """Data freshness level."""
    FRESH = "fresh"       # < 1 min
    ACCEPTABLE = "acceptable"  # 1-5 min
    STALE = "stale"       # 5-15 min
    EXPIRED = "expired"   # > 15 min


@dataclass
class QuoteSnapshot:
    """Quote with timestamp and freshness."""
    code: str
    price: float
    change: float
    change_pct: float
    volume: int
    timestamp: datetime
    source: str = "unknown"

    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.timestamp).total_seconds()

    @property
    def freshness(self) -> DataFreshness:
        age = self.age_seconds
        if age < 60:
            return DataFreshness.FRESH
        elif age < 300:
            return DataFreshness.ACCEPTABLE
        elif age < 900:
            return DataFreshness.STALE
        return DataFreshness.EXPIRED


class MarketDataMonitor:
    """Monitor market data freshness and accuracy."""

    def __init__(self):
        self._quotes: dict[str, QuoteSnapshot] = {}
        self._subscribers: list[Callable] = []
        self._update_count = 0
        self._error_count = 0
        self._last_check = datetime.now()
        logger.info("MarketDataMonitor initialized")

    def update_quote(
        self,
        code: str,
        price: float,
        change: float = 0,
        change_pct: float = 0,
        volume: int = 0,
        source: str = "unknown"
    ) -> QuoteSnapshot:
        """Update a quote and track freshness."""
        snapshot = QuoteSnapshot(
            code=code,
            price=price,
            change=change,
            change_pct=change_pct,
            volume=volume,
            timestamp=datetime.now(),
            source=source,
        )

        self._quotes[code] = snapshot
        self._update_count += 1

        for subscriber in self._subscribers:
            try:
                subscriber(code, snapshot)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

        return snapshot

    def get_quote(self, code: str) -> QuoteSnapshot | None:
        """Get current quote snapshot."""
        return self._quotes.get(code)

    def get_quotes(self, codes: list[str]) -> dict[str, QuoteSnapshot]:
        """Get multiple quotes."""
        return {code: self._quotes[code] for code in codes if code in self._quotes}

    def check_freshness(self, code: str) -> DataFreshness:
        """Check data freshness for a code."""
        snapshot = self._quotes.get(code)
        if not snapshot:
            return DataFreshness.EXPIRED
        return snapshot.freshness

    def get_stale_codes(self, max_age_seconds: int = 300) -> list[str]:
        """Get codes with stale data."""
        stale = []
        now = datetime.now()

        for code, snapshot in self._quotes.items():
            if (now - snapshot.timestamp).total_seconds() > max_age_seconds:
                stale.append(code)

        return stale

    def subscribe(self, callback: Callable[[str, QuoteSnapshot], None]):
        """Subscribe to quote updates."""
        self._subscribers.append(callback)

    def get_stats(self) -> dict[str, Any]:
        """Get monitor statistics."""
        datetime.now()

        freshness_counts = {
            "fresh": 0,
            "acceptable": 0,
            "stale": 0,
            "expired": 0,
        }

        for snapshot in self._quotes.values():
            freshness_counts[snapshot.freshness.value] += 1

        return {
            "total_codes": len(self._quotes),
            "update_count": self._update_count,
            "error_count": self._error_count,
            "freshness": freshness_counts,
            "last_check": self._last_check.isoformat(),
        }


class DataValidator:
    """Validate market data accuracy."""

    @staticmethod
    def validate_price(price: float) -> bool:
        """Validate price is reasonable."""
        return 0.01 < price < 100000

    @staticmethod
    def validate_change(change: float, price: float) -> bool:
        """Validate price change is reasonable."""
        if price == 0:
            return False
        pct = abs(change / price * 100)
        return pct < 50

    @staticmethod
    def validate_volume(volume: int) -> bool:
        """Validate volume is reasonable."""
        return 0 <= volume < 1000000000

    @staticmethod
    def validate_ohlc(open_p: float, high: float, low: float, close: float) -> bool:
        """Validate OHLC relationship."""
        if not all([open_p, high, low, close]):
            return False
        if high < low:
            return False
        if close > high or close < low:
            return False
        if open > high or open < low:
            return False
        return True

    @staticmethod
    def validate_quote(data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate complete quote data."""
        errors = []

        price = data.get("price", 0)
        if not DataValidator.validate_price(price):
            errors.append(f"Invalid price: {price}")

        change = data.get("change", 0)
        if not DataValidator.validate_change(change, price):
            errors.append(f"Invalid change: {change}")

        volume = data.get("volume", 0)
        if not DataValidator.validate_volume(volume):
            errors.append(f"Invalid volume: {volume}")

        ohlc_valid = DataValidator.validate_ohlc(
            data.get("open", 0),
            data.get("high", 0),
            data.get("low", 0),
            data.get("close", 0),
        )
        if not ohlc_valid:
            errors.append("Invalid OHLC relationship")

        return len(errors) == 0, errors


class DataCache:
    """High-performance data cache with TTL."""

    def __init__(self, default_ttl: int = 60):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]
        age = (datetime.now() - timestamp).total_seconds()

        if age > self._default_ttl:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: int | None = None):
        """Set value in cache."""
        ttl = ttl or self._default_ttl
        self._cache[key] = (value, datetime.now())

    def invalidate(self, key: str):
        """Invalidate a key."""
        self._cache.pop(key, None)

    def clear(self):
        """Clear all cache."""
        self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = len(self._cache)
        now = datetime.now()
        valid = sum(1 for _, ts in self._cache.values() if (now - ts).total_seconds() < self._default_ttl)

        return {
            "total_keys": total,
            "valid_keys": valid,
            "expired_keys": total - valid,
        }


_monitor = MarketDataMonitor()
_cache = DataCache()


def get_market_monitor() -> MarketDataMonitor:
    """Get global market data monitor."""
    return _monitor


def get_data_cache() -> DataCache:
    """Get global data cache."""
    return _cache


__all__ = [
    "DataFreshness",
    "QuoteSnapshot",
    "MarketDataMonitor",
    "DataValidator",
    "DataCache",
    "get_market_monitor",
    "get_data_cache",
]
