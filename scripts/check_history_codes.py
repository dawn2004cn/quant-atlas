from app.infrastructure.database.stock_cache_db import StockCache

cache = StockCache.default()
conn = cache._adapter.get_connection()
cur = conn.cursor()

for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
    cur.execute(f'SELECT COUNT(*) FROM {table}')
    total = cur.fetchone()[0]
    cur.execute(f'SELECT COUNT(*) FROM {table} WHERE stock_code NOT LIKE "CN%%"')
    no_cn = cur.fetchone()[0]
    print(f'{table}: total={total}, no CN:={no_cn}')

cur.close()
conn.close()