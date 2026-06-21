#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查MySQL锁配置和当前状态"""

import os
from dotenv import load_dotenv
load_dotenv()

from app.config import AppSettings
settings = AppSettings.from_env()

import pymysql
from urllib.parse import urlparse

url = urlparse(settings.database_uri)
host = url.hostname
port = url.port or 3306
user = url.username
password = url.password
database = url.path[1:]

print(f'连接到: {host}:{port}')
print(f'数据库: {database}')

try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connect_timeout=30
    )
    cursor = conn.cursor()
    
    # 检查锁等待超时配置
    print('\n=== InnoDB 锁等待超时配置 ===')
    cursor.execute("SHOW VARIABLES LIKE 'innodb_lock_wait_timeout'")
    result = cursor.fetchone()
    print(f'innodb_lock_wait_timeout: {result[1]} 秒')
    
    # 检查事务隔离级别
    print('\n=== 事务隔离级别 ===')
    cursor.execute("SHOW VARIABLES LIKE 'transaction_isolation'")
    result = cursor.fetchone()
    print(f'transaction_isolation: {result[1]}')
    
    # 检查当前运行的进程
    print('\n=== 当前运行的进程 ===')
    cursor.execute('SHOW PROCESSLIST')
    processes = cursor.fetchall()
    
    print(f'{"ID":<6} {"User":<12} {"Host":<25} {"DB":<15} {"Command":<12} {"Time":<8} {"State":<30}')
    print('=' * 100)
    
    long_running = []
    for proc in processes:
        pid, user, host, db, command, time, state, info = proc
        if time > 60:
            long_running.append(pid)
        if time > 10 or command != 'Sleep':
            print(f'{pid:<6} {user:<12} {host:<25} {str(db):<15} {command:<12} {time:<8} {str(state):<30}')
    
    if long_running:
        print(f'\n发现长时间运行的进程: {long_running}')
        print('建议终止这些进程')
    
    # 检查表锁情况
    print('\n=== 表锁情况 ===')
    cursor.execute("SHOW OPEN TABLES WHERE In_use > 0")
    tables = cursor.fetchall()
    if tables:
        for table in tables:
            print(f'数据库: {table[0]}, 表: {table[1]}, 使用次数: {table[2]}')
    else:
        print('没有表被锁定')
    
    conn.close()
    
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
