import sys
sys.path.insert(0, r'/')

from app.infrastructure.database.stock_cache_db import StockCache
from app.domain.enums import MarketCode
from datetime import datetime

# Test get_all_stocks output
cache = StockCache()
rows = cache.get_all_stocks(max_age_minutes=1440)
print('Total rows:', len(rows))

# Check the format
market = MarketCode.CN
prefix = f"{market.value}:"
quotes = []
for r in rows[:10]:
    code = str(r.get("code", ""))
    print(f'Code: {code}, startswith {prefix}: {code.startswith(prefix)}')
    if code.startswith(prefix):
        quotes.append(code)
    elif market == MarketCode.CN and code.isdigit() and len(code) == 6:
        quotes.append(code)

print('Matched quotes:', len(quotes))