from app.config import AppSettings
from app.infrastructure.database.db_manager import get_session
from sqlalchemy import text

settings = AppSettings.from_env()
session = get_session(settings.mysql)

# Check user_stock_group_stocks table
result = session.execute(text('SELECT * FROM user_stock_group_stocks LIMIT 10')).fetchall()
print('Sample stocks in groups:')
for r in result[:5]:
    print(r)

# Check specific group
result2 = session.execute(text('SELECT * FROM user_stock_group_stocks WHERE group_id = 1 LIMIT 10')).fetchall()
print('\nGroup 1 stocks:')
for r in result2[:10]:
    print(r)