
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查2026-04-23到最新日期的数据是否存在"""

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

mysql_host = os.getenv('MYSQL_HOST', 'localhost')
mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
mysql_user = os.getenv('MYSQL_USER', 'root')
mysql_password = os.getenv('MYSQL_PASSWORD', '')
mysql_db = os.getenv('MYSQL_DATABASE', 'quant_platform')

print(f"Connecting to MySQL: {mysql_host}:{mysql_port}/{mysql_db}")

try:
    conn = pymysql.connect(
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_db,
        charset='utf8mb4'
    )
    
    print("Connected successfully!")
    
    cur = conn.cursor()
    
    start_date = "2026-04-23"
    tables = ["stock_history_sh", "stock_history_sz", "stock_history_bj", "stock_history"]
    
    print(f"\n检查日期范围: {start_date} 到 当前")
    print("=" * 60)
    
    total_rows = 0
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE date >= %s", (start_date,))
            count = cur.fetchone()[0]
            total_rows += count
            print(f"{table}: {count} 行")
        except Exception as e:
            print(f"{table}: 查询失败 - {e}")
    
    print("=" * 60)
    print(f"总计: {total_rows} 行")
    
    # 检查最新日期
    print("\n各表最新日期:")
    max_dates = []
    for table in tables:
        try:
            cur.execute(f"SELECT MAX(date) FROM {table}")
            result = cur.fetchone()[0]
            if result:
                max_dates.append(str(result))
                print(f"{table}: {result}")
        except Exception as e:
            print(f"{table}: 查询失败 - {e}")
    
    if max_dates:
        print(f"\n最新日期: {max(max_dates)}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
