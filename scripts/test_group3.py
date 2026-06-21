from app.config import AppSettings
from app.infrastructure.database.db_manager import get_session
from sqlalchemy import text

settings = AppSettings.from_env()
session = get_session(settings.mysql)

# Check specific columns
result = session.execute(text('SELECT group_id, symbol, user_id FROM stock_group_items WHERE group_id = 1 AND is_removed = 0 LIMIT 10')).fetchall()
print('Group 1 stocks (explicit columns):')
for r in result:
    print(f'  group_id={r[0]}, symbol={r[1]}, user_id={r[2]}')