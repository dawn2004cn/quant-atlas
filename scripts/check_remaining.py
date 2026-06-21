import pymysql

import os, sys
conn = pymysql.connect(
    host=os.environ.get("MYSQL_HOST", '192.168.8.103'),
    port=int(os.environ.get("MYSQL_PORT", "3307")),
    user=os.environ.get("MYSQL_USER", 'admin'),
    password=os.environ.get("MYSQL_PASSWORD") or "",
    database=os.environ.get("MYSQL_DATABASE", 'quant_atlas'),
    connect_timeout=15,
    read_timeout=30,
    write_timeout=30
)
if not os.environ.get("MYSQL_PASSWORD"):
    print("WARNING: Using default DB password. Set MYSQL_PASSWORD env var.", file=sys.stderr)
cur = conn.cursor()

for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
    cur.execute(f'SELECT COUNT(DISTINCT stock_code) FROM {table} WHERE stock_code NOT LIKE "CN%%"')
    remaining = cur.fetchone()[0]
    print(f'{table}: {remaining} codes without CN:')

cur.close()
conn.close()