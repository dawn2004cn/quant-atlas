import pymysql

import os, sys
conn = pymysql.connect(
    host=os.environ.get("MYSQL_HOST", '192.168.8.103'),
    port=int(os.environ.get("MYSQL_PORT", "3307")),
    user=os.environ.get("MYSQL_USER", 'admin'),
    password=os.environ.get("MYSQL_PASSWORD") or "",
    database=os.environ.get("MYSQL_DATABASE", 'quant_atlas')
)
if not os.environ.get("MYSQL_PASSWORD"):
    print("WARNING: Using default DB password. Set MYSQL_PASSWORD env var.", file=sys.stderr)
cur = conn.cursor()

print('=== stock_groups ===')
cur.execute('SELECT * FROM stock_groups')
for row in cur.fetchall():
    print(row)

print('\n=== stock_group_items ===')
cur.execute('SELECT * FROM stock_group_items LIMIT 20')
for row in cur.fetchall():
    print(row)

conn.close()