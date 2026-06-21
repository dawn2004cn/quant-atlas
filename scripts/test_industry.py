from app.config import AppSettings
from app.infrastructure.database.db_manager import get_session
from sqlalchemy import text

settings = AppSettings.from_env()
session = get_session(settings.mysql)

# Check specific stocks
codes = ['688012', '688008', '600519', '000001']
for code in codes:
    result = session.execute(text('SELECT code, name, industry FROM base_stock_reference WHERE code = :code'), {'code': code}).fetchone()
    if result:
        print(f'{result[0]}: name={result[1]}, industry="{result[2]}"')
    else:
        print(f'{code}: not found in table')