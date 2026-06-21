
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清理MySQL中的无效日期"""

import os
import pymysql
from dotenv import load_dotenv
from datetime import datetime

# Add project root to path for shared utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.core.utils.sql_utils import validate_identifier

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
    
    for table in tables:
        if not validate_identifier(table):
            print(f"  Skipping invalid table name: {table}")
            continue
        print(f"\nChecking {table}...")
        
        # 查询所有日期
        try:
            cur.execute(f"SELECT DISTINCT date FROM {table}")
            dates = cur.fetchall()
            
            invalid_dates = []
            
            for (date_str,) in dates:
                if date_str is None:
                    continue
                try:
                    datetime.strptime(str(date_str), "%Y-%m-%d")
                except ValueError:
                    invalid_dates.append(date_str)
            
            if invalid_dates:
                print(f"  Found {len(invalid_dates)} invalid dates:")
                for d in invalid_dates[:10]:
                    print(f"    - {d}")
                if len(invalid_dates) > 10:
                    print(f"    ... and {len(invalid_dates) - 10} more")
                
                # 删除无效日期的记录
                delete_count = 0
                for invalid_date in invalid_dates:
                    try:
                        cur.execute(f"DELETE FROM {table} WHERE date = %s", (invalid_date,))
                        delete_count += cur.rowcount
                    except Exception as e:
                        print(f"  Error deleting {invalid_date}: {e}")
                
                conn.commit()
                print(f"  Deleted {delete_count} records with invalid dates")
            else:
                print(f"  No invalid dates found")
                
        except Exception as e:
            print(f"Error checking {table}: {e}")
    
    # 再次检查最新日期
    print("\n" + "=" * 60)
    print("Latest valid dates after cleanup:")
    max_dates = []
    for table in tables:
        try:
            cur.execute(f"SELECT MAX(date) as max_date FROM {table}")
            result = cur.fetchone()
            if result and result[0]:
                max_date = str(result[0])
                max_dates.append(max_date)
                print(f"{table}: {max_date}")
        except Exception as e:
            print(f"{table}: Error - {e}")
    
    if max_dates:
        print(f"\nOverall latest date: {max(max_dates)}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
