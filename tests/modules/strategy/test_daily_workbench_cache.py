from __future__ import annotations

from unittest.mock import MagicMock

from app.domain.enums import MarketCode
from app.infrastructure.memory_cache import MemoryCache
from app.modules.strategy.services.analytics.daily_workbench_service import DailyWorkbenchService


def test_build_snapshot_hits_short_ttl_cache() -> None:
    market = MagicMock()
    market.get_panorama.return_value = {"up": 10, "down": 5, "flat": 1}
    market.get_sentiment.return_value = {"score": 50, "level": "中性", "stats": {}}
    market.list_quotes.return_value = []
    watchlist = MagicMock()
    watchlist.list_symbols.return_value = []

    cache = MemoryCache(default_ttl=45, maxsize=64)
    svc = DailyWorkbenchService(
        market_service=market,
        watchlist_service=watchlist,
        snapshot_cache=cache,
        snapshot_cache_ttl=45,
    )

    first = svc.build_snapshot(1, market=MarketCode.CN, watchlist_limit=12)
    second = svc.build_snapshot(1, market=MarketCode.CN, watchlist_limit=12)

    assert first["market"] == "CN"
    assert second is first or second["generated_at"] == first["generated_at"]
    assert market.get_panorama.call_count == 1
    assert first.get("_cache") in (None, "miss")
    # Second payload should be marked hit when cache layer annotates
    assert second.get("_cache") == "hit" or market.get_panorama.call_count == 1
