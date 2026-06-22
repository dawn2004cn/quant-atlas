#!/usr/bin/env python3
"""检查MySQL各市场最新日期"""

import sys
from pathlib import Path

# Add project root to path
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
    cursor.execute(f'SELECT MAX(trade_date) FROM stock_day_kline_{market}')
    result = cursor.fetchone()
    print(f'{market}: {result[0]}')

cursor.close()
conn.close()