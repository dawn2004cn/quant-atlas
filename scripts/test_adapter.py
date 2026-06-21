from datetime import date, timedelta
from app.infrastructure.providers.history_adapters import MultiSourceHistoryProvider

provider = MultiSourceHistoryProvider()
end = date.today()
start = end - timedelta(days=30)

# Test with 600519
result = provider.get_history('600519', 'CN', start, end)
print(f'Total bars from all adapters: {len(result)}')
if result:
    print('First bar:', result[0])
    print('Last bar:', result[-1])