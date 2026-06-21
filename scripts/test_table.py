from app.config import AppSettings
from app.infrastructure.database.db_manager import get_session
from sqlalchemy import text

settings = AppSettings.from_env()
session = get_session(settings.mysql)

# Check tables
result = session.execute(text('SHOW TABLES')).fetchall()
print('Tables in quant_atlas:')
for r in result:
    print(f'  {r[0]}')