from app.config import AppSettings
from app.infrastructure.database.adapters import MysqlAdapter
from app.infrastructure.database.history_repository import HistoryRepository

settings = AppSettings.from_env()
db = MysqlAdapter(settings.mysql)
repo = HistoryRepository(db)

# Test with 600519
result = repo.get_history('600519', '2024-01-01', '2024-12-31', limit=100)
print(f'get_history for 600519: {len(result)} bars')
if result:
    print('First bar:', result[0])

# Test get_history_latest
result2 = repo.get_history_latest('600519', limit=10)
print(f'get_history_latest for 600519: {len(result2)} bars')
if result2:
    print('Latest bar:', result2[-1])