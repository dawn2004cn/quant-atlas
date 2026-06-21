
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""终止阻塞的MySQL进程"""

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
    
    # 终止长时间运行的查询
    print("终止阻塞的进程...")
    
    # 终止运行超过300秒的查询
    cur.execute("SHOW PROCESSLIST")
    processes = cur.fetchall()
    
    for proc in processes:
        proc_id = proc[0]
        command = proc[4]
        time = proc[5]
        info = proc[7] if len(proc) > 7 else ""
        
        # 跳过系统进程和event_scheduler
        if command in ['Daemon', 'Sleep']:
            continue
        
        # 终止运行超过5分钟的查询
        if time > 300:
            print(f"终止进程 {proc_id}: {command} (运行 {time} 秒) - {info[:50]}")
            try:
                cur.execute(f"KILL {proc_id}")
                print(f"进程 {proc_id} 已终止")
            except Exception as e:
                print(f"终止进程 {proc_id} 失败: {e}")
    
    cur.close()
    conn.close()
    
    print("\n完成！")
    
except Exception as e:
    print(f"Error: {e}")
