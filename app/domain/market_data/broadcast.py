from __future__ import annotations

"""Centralized Market Data Broadcast.

Implements from strategy_plan2.md:
- Market data synchronization engine
- Memory bus broadcasting
- Per-manager watchlist sharding

Usage:
    broadcaster = MarketDataBroadcaster()
    broadcaster.broadcast_to_watchlists(watchlists, market_snapshot)
    data = broadcaster.subscribe("manager_001", ["SH600519", "SH000001"])
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MarketTick:
    """Single market tick."""
    symbol: str
    last: float
    volume: int
    timestamp: datetime = field(default_factory=datetime.now)
    bid: float = 0.0
    ask: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    change: float = 0.0


@dataclass
class MarketSnapshot:
    """Snapshot of market data."""
    snapshot_id: str
    timestamp: datetime
    ticks: dict[str, MarketTick] = field(default_factory=dict)


@dataclass
class WatchlistData:
    """Data for a watchlist."""
    manager_id: str
    symbols: list[str]
    snapshot: MarketSnapshot | None = None


class MarketDataBroadcaster:
    """Centralized market data broadcaster."""

    def __init__(self):
        self._watchlists: dict[str, list[str]] = {}
        self._tick_cache: dict[str, MarketTick] = {}
        self._shards: dict[int, list[str]] = {}

    def register_watchlist(
        self,
        manager_id: str,
        symbols: list[str],
    ) -> None:
        """Register manager watchlist."""
        self._watchlists[manager_id] = symbols
        shard_id = hash(manager_id) % 10

        if shard_id not in self._shards:
            self._shards[shard_id] = []
        self._shards[shard_id].append(manager_id)

        logger.info(f"Registered watchlist for {manager_id} with {len(symbols)} symbols")

    def update_ticks(
        self,
        symbols: list[str],
        ticks: dict[str, dict],
    ) -> None:
        """Update market ticks."""
        for symbol in symbols:
            if symbol not in ticks:
                continue

            tick_data = ticks[symbol]
            self._tick_cache[symbol] = MarketTick(
                symbol=symbol,
                last=tick_data.get("last", 0.0),
                volume=tick_data.get("volume", 0),
                bid=tick_data.get("bid", 0.0),
                ask=tick_data.get("ask", 0.0),
                open=tick_data.get("open", 0.0),
                high=tick_data.get("high", 0.0),
                low=tick_data.get("low", 0.0),
                change=tick_data.get("change", 0.0),
            )

        logger.debug(f"Updated {len(symbols)} ticks in cache")

    def subscribe(
        self,
        manager_id: str,
        symbols: list[str] = None,
    ) -> dict[str, MarketTick]:
        """Subscribe to market data."""
        if manager_id not in self._watchlists:
            return {}

        watchlist = self._watchlists[manager_id]
        subscribe_symbols = symbols or watchlist

        result = {}
        for symbol in subscribe_symbols:
            if symbol in self._tick_cache:
                result[symbol] = self._tick_cache[symbol]

        return result

    def get_snapshot(
        self,
        symbols: list[str] = None,
    ) -> MarketSnapshot:
        """Get current market snapshot."""
        snapshot_symbols = symbols or list(self._tick_cache.keys())

        ticks = {
            s: self._tick_cache[s]
            for s in snapshot_symbols
            if s in self._tick_cache
        }

        return MarketSnapshot(
            snapshot_id=str(uuid4())[:8],
            timestamp=datetime.now(),
            ticks=ticks,
        )

    def broadcast_to_watchlists(
        self,
        market_data: dict[str, dict],
    ) -> int:
        """Broadcast market data to all watchlists."""
        symbols = list(market_data.keys())
        self.update_ticks(symbols, market_data)

        watchers = set()
        for manager_id in self._watchlists:
            for symbol in self._watchlists[manager_id]:
                if symbol in market_data:
                    watchers.add(manager_id)
                    break

        logger.info(f"Broadcast to {len(watchers)} managers")
        return len(watchers)

    def get_shard_info(self) -> dict[int, list[str]]:
        """Get sharding info."""
        return self._shards.copy()

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_ticks": len(self._tick_cache),
            "watchlist_count": len(self._watchlists),
            "shard_count": len(self._shards),
            "symbols": list(self._tick_cache.keys())[:10],
        }


class MarketDataProxy:
    """Proxy for market data access with caching."""

    def __init__(self, broadcaster: MarketDataBroadcaster = None):
        self._broadcaster = broadcaster or MarketDataBroadcaster()
        self._cache: dict[str, MarketTick] = {}

    def get_bars(
        self,
        symbols: list[str],
        manager_id: str,
    ) -> dict[str, list[MarketTick]]:
        """Get bars for symbols."""
        ticks = self._broadcaster.subscribe(manager_id, symbols)

        result = {}
        for symbol, tick in ticks.items():
            result[symbol] = [tick]

        return result


_global_broadcaster: MarketDataBroadcaster | None = None


def get_market_broadcaster() -> MarketDataBroadcaster:
    """Get global market broadcaster."""
    global _global_broadcaster
    if _global_broadcaster is None:
        _global_broadcaster = MarketDataBroadcaster()
    return _global_broadcaster
