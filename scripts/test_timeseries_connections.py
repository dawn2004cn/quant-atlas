#!/usr/bin/env python3
"""测试QuestDB和TimescaleDB连接"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
except ImportError:
    print('psycopg2未安装，尝试使用psycopg2-binary')
    try:
        import psycopg2
    except ImportError:
        print('请安装psycopg2或psycopg2-binary')
        sys.exit(1)

from app.core.runtime_config import get_runtime, get_runtime_int

print('=== QuestDB PG端口测试 ===')
try:
    conn = psycopg2.connect(
        host=get_runtime('QUESTDB_HOST', '127.0.0.1'),
        port=get_runtime_int('QUESTDB_PG_PORT', 8813),
        user=get_runtime('QUESTDB_USER', 'admin'),
        password=get_runtime('QUESTDB_PASSWORD', ''),
        database=get_runtime('QUESTDB_DATABASE', 'qdb')
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock_history")
    result = cursor.fetchone()
    print(f'QuestDB PG连接成功，行数: {result[0]}')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'QuestDB PG连接失败: {e}')

print()
print('=== TimescaleDB测试 ===')
try:
    conn = psycopg2.connect(
        host=get_runtime('TIMESCALEDB_HOST', '127.0.0.1'),
        port=get_runtime_int('TIMESCALEDB_PORT', 5432),
        user=get_runtime('TIMESCALEDB_USER', 'postgres'),
        password=get_runtime('TIMESCALEDB_PASSWORD', ''),
        database=get_runtime('TIMESCALEDB_DATABASE', 'quant_atlas')
    )
    cursor = conn.cursor()
    # 检查是否有stock_history表
    cursor.execute("SELECT to_regclass('stock_history')")
    result = cursor.fetchone()
    if result[0]:
        cursor.execute("SELECT COUNT(*) FROM stock_history")
        count = cursor.fetchone()
        print(f'TimescaleDB连接成功，stock_history表存在，行数: {count[0]}')
    else:
        print('TimescaleDB连接成功，但stock_history表不存在')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'TimescaleDB连接失败: {e}')