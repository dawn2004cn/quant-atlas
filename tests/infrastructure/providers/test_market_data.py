import pytest
from app.infrastructure.providers.market_data import MultiSourceMarketProvider
from app.domain.enums import MarketCode
from app.infrastructure.database.stock_cache_db import StockCache

@pytest.fixture
def provider():
    cache = StockCache.default()
    return MultiSourceMarketProvider(cache=cache)

def test_get_realtime_quotes_cn(provider):
    """Test fetching realtime quotes for A-share."""
    # Using a common stock like Ping An (000001)
    quotes = provider.get_realtime_quotes(['000001'], MarketCode.CN)
    assert isinstance(quotes, list)
    if quotes:
        q = quotes[0]
        assert q.code in ['000001', 'sh600000', 'sz000001'] # depending on normalization
        assert q.price >= 0

def test_get_full_market_quotes(provider):
    """Test fetching full market quotes (mostly from cache)."""
    quotes = provider.get_realtime_quotes(market=MarketCode.CN)
    assert isinstance(quotes, list)
    # Should have a significant number of stocks if cache is populated
    assert len(quotes) > 100 

def test_get_stock_history(provider):
    """Test fetching stock history."""
    # Use a common stock
    hist = provider.get_stock_history('000001', MarketCode.CN, start='2024-01-01', end='2024-01-10')
    assert isinstance(hist, list)
    # Even if empty (due to network), it shouldn't crash
    if hist:
        assert 'date' in hist[0]
        assert 'close' in hist[0]

def test_get_market_rankings(provider):
    """Test market rankings (gainers, losers, etc.)."""
    rankings = provider.get_market_rankings(MarketCode.CN)
    assert isinstance(rankings, dict)
    assert 'gainers' in rankings
    assert 'losers' in rankings
    assert 'amounts' in rankings
    assert 'turnovers' in rankings
