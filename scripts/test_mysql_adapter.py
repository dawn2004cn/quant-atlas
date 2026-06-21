from datetime import date, timedelta
from app.infrastructure.providers.history_adapters import SqliteHistoryAdapter
from app.domain.enums import MarketCode

adapter = SqliteHistoryAdapter()
end = date.today()
start = end - timedelta(days=30)

# Test with 600519
result = adapter.get_history('600519', MarketCode.CN, start, end)
print(f'MySQL adapter result: {len(result)} bars')
if result:
    print('First bar:', result[0])