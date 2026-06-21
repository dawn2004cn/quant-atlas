import pymysql

import os, sys
conn = pymysql.connect(
    host=os.environ.get("MYSQL_HOST", '192.168.8.103'),
    port=int(os.environ.get("MYSQL_PORT", "3307")),
    user=os.environ.get("MYSQL_USER", 'admin'),
    password=os.environ.get("MYSQL_PASSWORD") or "",
    database=os.environ.get("MYSQL_DATABASE", 'quant_atlas'),
    connect_timeout=10,
    read_timeout=30
)
if not os.environ.get("MYSQL_PASSWORD"):
    print("WARNING: Using default DB password. Set MYSQL_PASSWORD env var.", file=sys.stderr)
cur = conn.cursor()

for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
    print(f'Checking {table}...')
    
    # Just get sample codes without counting all rows
    cur.execute(f'SELECT DISTINCT stock_code FROM {table} LIMIT 10')
    samples = [r[0] for r in cur.fetchall()]
    print(f'  samples: {samples}')
    
    # Check format patterns
    cn_count = 0
    no_cn_count = 0
    for code in samples:
        if code.startswith('CN:'):
            cn_count += 1
        else:
            no_cn_count += 1
    
    print(f'  in sample: CN_prefix={cn_count}, no_CN_prefix={no_cn_count}')
    print()

cur.close()
conn.close()
print('Done!')
