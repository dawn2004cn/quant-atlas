
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查MySQL中最新的日期 - 超级简化版"""

import os
import pymysql
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# MySQL 连接配置
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
