import sys
sys.path.insert(0, r'/')

from app.infrastructure.database.stock_cache_db import StockCache
from app.infrastructure.providers.market_data import MarketDataProvider
from app.domain.enums import MarketCode

cache = StockCache()
print('Cache mode:', cache._mode)

# Test directly
rows = cache.get_all_stocks(max_age_minutes=1440)
print('Direct get_all_stocks:', len(rows))

# Test provider
provider = MarketDataProvider(cache)
quotes = provider.get_realtime_quotes(market=MarketCode.CN)
print('Provider quotes:', len(quotes))
if quotes:
    print('Sample quote:', quotes[0])