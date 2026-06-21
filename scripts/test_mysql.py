import sys
sys.path.insert(0, r'/')

from app.infrastructure.database.stock_cache_db import StockCache
from datetime import datetime, timedelta

cache = StockCache()
cutoff = (datetime.now() - timedelta(minutes=1440)).strftime("%Y-%m-%d %H:%M:%S")
print('Cutoff:', cutoff)

import pymysql
import os, sys
_pw = os.environ.get("MYSQL_PASSWORD") or ""
if not os.environ.get("MYSQL_PASSWORD"):
    print("WARNING: Using default DB password. Set MYSQL_PASSWORD env var.", file=sys.stderr)
conn = pymysql.connect(host=os.environ.get("MYSQL_HOST", '192.168.8.103'), port=int(os.environ.get("MYSQL_PORT", "3307")), user=os.environ.get("MYSQL_USER", 'root'), password=_pw, database=os.environ.get("MYSQL_DATABASE", 'quant_atlas'))
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM stocks WHERE update_time > %s", (cutoff,))
print('Fresh count:', cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM stocks")
print('Total count:', cur.fetchone()[0])

cur.execute("SELECT update_time FROM stocks ORDER BY update_time DESC LIMIT 3")
print('Latest update_time:', cur.fetchall())
conn.close()