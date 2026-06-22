#!/usr/bin/env python3
"""检查MySQL各市场最新日期"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pymysql
from app.core.runtime_config import get_runtime, get_runtime_int

conn = pymysql.connect(
    host=get_runtime('MYSQL_HOST', '127.0.0.1'),
    port=get_runtime_int('MYSQL_PORT', 3306),
    user=get_runtime('MYSQL_USER', 'admin'),
    password=get_runtime('MYSQL_PASSWORD', ''),
    database=get_runtime('MYSQL_DATABASE', 'quant_atlas')
)

cursor = conn.cursor()

markets = ['sh', 'sz', 'bj']
for market in markets:
    table = f'stock_history_{market}'
    cursor.execute(f'SELECT MAX(`date`) FROM {table}')
    result = cursor.fetchone()
    print(f'{market}: {result[0]}')

cursor.close()
conn.close()