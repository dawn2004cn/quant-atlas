"""检查MySQL同步进度"""
import sys
sys.path.insert(0, '.')

from app.config import get_settings
import pymysql

settings = get_settings()
conn = pymysql.connect(
    host=settings.mysql.host,
    port=settings.mysql.port,
    user=settings.mysql.user,
    password=settings.mysql.password,
    db=settings.mysql.database
)

count = 0
with conn.cursor() as cur:
    for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
        try:
            cur.execute(f'SELECT COUNT(DISTINCT stock_code) FROM {table}')
            row = cur.fetchone()
            if row:
                count += row[0]
        except:
            pass
conn.close()

print(f'MySQL股票数: {count}')
print(f'CSV股票数: 9956')
print(f'进度: {round(count/9956*100, 1)}%')
print(f'剩余: {9956-count}只')
