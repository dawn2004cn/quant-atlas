
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""删除那个特定的无效日期"""

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
    
    # 删除 stock_history_sh 中的无效日期
    bad_date = "8636-15-74"
    
    print(f"Deleting records with date: {bad_date}")
    
    cur.execute("DELETE FROM stock_history_sh WHERE date = %s", (bad_date,))
    deleted = cur.rowcount
    conn.commit()
    print(f"Deleted {deleted} records from stock_history_sh")
    
    # 再次检查最新日期
    print("\nChecking latest dates:")
    tables = ["stock_history_sh", "stock_history_sz", "stock_history_bj", "stock_history"]
    max_dates = []
    for table in tables:
        cur.execute(f"SELECT MAX(date) as max_date FROM {table}")
        result = cur.fetchone()
        if result and result[0]:
            max_date = str(result[0])
            max_dates.append(max_date)
            print(f"{table}: {max_date}")
    
    if max_dates:
        print(f"\nOverall latest date: {max(max_dates)}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
