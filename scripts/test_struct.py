from app.config import AppSettings
from app.infrastructure.database.db_manager import get_session
from sqlalchemy import text

settings = AppSettings.from_env()
session = get_session(settings.mysql)

# Check table structure
result = session.execute(text('DESCRIBE stock_group_items')).fetchall()
print('stock_group_items structure:')
for r in result:
    print(f'  {r[0]}: {r[1]}')