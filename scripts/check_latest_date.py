
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查MySQL中最新的日期"""

from pathlib import Path
import sys

# 添加项目根目录到路径
base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect

settings = AppSettings.from_env()
ms = settings.mysql

if not ms:
    print("MySQL not configured")
    sys.exit(1)

try:
    conn = mysql_connect(ms)
    if conn is None:
        print("Cannot connect to MySQL")
        sys.exit(1)
    
    cur = conn.cursor()
    
    tables = ["stock_history_sh", "stock_history_sz", "stock_history_bj", "stock_history"]
    max_dates = []
    
    for table in tables:
        try:
            cur.execute(f"SELECT MAX(date) as max_date FROM {table}")
            result = cur.fetchone()
            if result and result[0]:
                max_date = str(result[0])
                max_dates.append(max_date)
                print(f"{table} latest date: {max_date}")
            else:
                print(f"{table} is empty or no date")
        except Exception as e:
            print(f"Error querying {table}: {e}")
    
    if max_dates:
        print(f"\nOverall latest date: {max(max_dates)}")
    else:
        print("\nNo date data found")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

