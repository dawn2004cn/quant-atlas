import pymysql
from app.config import get_settings

s = get_settings()
conn = pymysql.connect(host=s.mysql.host, port=s.mysql.port, user=s.mysql.user, password=s.mysql.password, db=s.mysql.database)
cur = conn.cursor()

for code in ['sh600686', 'sh600689', 'sh600690']:
    cur.execute("SELECT COUNT(*) FROM stock_history_sh WHERE stock_code=%s", (code,))
    count = cur.fetchone()[0]
    print(f"{code}: {count} rows")

conn.close()
