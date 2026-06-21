from app.infrastructure.database.stock_cache_db import StockCache
from app.infrastructure.providers.market_data import MultiSourceMarketProvider


def test_stock_cache_is_singleton_by_design():
    """``StockCache`` 使用 ``__new__`` 单例，与线程安全连接池设计一致。"""
    cache_a = StockCache()
    cache_b = StockCache()
    assert cache_a is cache_b


def test_stock_cache_default_is_shared_for_compatibility():
    default_a = StockCache.default()
    default_b = StockCache.default()
    assert default_a is default_b


def test_market_provider_accepts_injected_cache():
    injected_cache = StockCache()
    provider = MultiSourceMarketProvider(cache=injected_cache)
    assert provider._cache is injected_cache
