"""QuoteCache via CacheManager."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.infrastructure.cache.quote_cache import QuoteCache


def test_get_quotes_reads_from_cache_manager():
    cache = QuoteCache()
    mgr = MagicMock()
    mgr.get.return_value = {"price": 100}
    cache._cache = mgr

    result = cache.get_quotes(["600519"])
    assert result == {"600519": {"price": 100}}
    mgr.get.assert_called_once_with("quote:600519")


def test_set_quotes_writes_via_cache_manager():
    cache = QuoteCache()
    mgr = MagicMock()
    cache._cache = mgr

    cache.set_quotes({"600519": {"price": 101}})
    mgr.set.assert_called_once_with("quote:600519", {"price": 101}, ttl=60, memory_ttl=60)
