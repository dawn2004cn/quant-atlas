from app.config import AppSettings
from app.infrastructure.database.db_manager import get_session
from sqlalchemy import text

settings = AppSettings.from_env()
session = get_session(settings.mysql)

# Check all stocks in group 1
result = session.execute(text('SELECT group_id, symbol FROM stock_group_items WHERE group_id = 1 AND is_removed = 0')).fetchall()
print('All symbols in group 1:')
for r in result:
    print(f'  symbol="{r[1]}", len={len(r[1])}')