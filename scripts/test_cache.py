import sys
sys.path.insert(0, r'/')

from app.infrastructure.database.stock_cache_db import StockCache

cache = StockCache()
rows = cache.get_all_stocks(max_age_minutes=1440)
print('Rows count:', len(rows))
print('Sample:', rows[0] if rows else 'None')