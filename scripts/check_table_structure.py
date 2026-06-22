#!/usr/bin/env python3
"""检查stock_history_sh表结构"""

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
cursor.execute("DESCRIBE stock_history_sh")
for r in cursor.fetchall():
    print(r)

cursor.close()
conn.close()