from app.config import AppSettings
from app.infrastructure.database.db_manager import get_session
from sqlalchemy import text

settings = AppSettings.from_env()
session = get_session(settings.mysql)

# Check stock_group_items
result = session.execute(text('SELECT * FROM stock_group_items WHERE group_id = 1 AND is_removed = 0 LIMIT 20')).fetchall()
print('Group 1 stocks:')
for r in result:
    print(f'  symbol={r[2]}, group_id={r[0]}, user_id={r[1]}')