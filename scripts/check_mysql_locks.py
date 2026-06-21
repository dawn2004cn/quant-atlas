
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查MySQL锁状态"""

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

mysql_host = os.getenv('MYSQL_HOST', 'localhost')
mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
mysql_user = os.getenv('MYSQL_USER', 'root')
mysql_password = os.getenv('MYSQL_PASSWORD', '')
mysql_db = os.getenv('MYSQL_DATABASE', 'quant_platform')

try:
    conn = pymysql.connect(
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_db,
        charset='utf8mb4'
    )
    
    cur = conn.cursor()
    
    # 检查进程列表
    print("MySQL进程列表:")
    cur.execute("SHOW PROCESSLIST")
    processes = cur.fetchall()
    for proc in processes:
        print(f"ID: {proc[0]}, User: {proc[1]}, Host: {proc[2]}, DB: {proc[3]}, Command: {proc[4]}, Time: {proc[5]}, State: {proc[6]}")
    
    # 检查事务
    print("\n\n事务状态:")
    cur.execute("SELECT * FROM INFORMATION_SCHEMA.INNODB_TRX")
    trxs = cur.fetchall()
    if trxs:
        for trx in trxs:
            print(trx)
    else:
        print("没有活跃事务")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
