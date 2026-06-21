#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查MySQL阻塞进程"""

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

print(f'连接到: {host}:{port}')

try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database='information_schema',
        connect_timeout=30
    )
    cursor = conn.cursor()
    
    # 查看当前运行的事务
    print('\n=== 当前运行的事务 ===')
    cursor.execute("""
        SELECT * FROM INNODB_TRX
    """)
    trxs = cursor.fetchall()
    if trxs:
        for trx in trxs:
            print(f'事务ID: {trx[0]}, 状态: {trx[1]}, 开始时间: {trx[5]}, 等待锁: {trx[3]}')
    else:
        print('没有运行中的事务')
    
    # 查看锁等待
    print('\n=== 锁等待情况 ===')
    cursor.execute("""
        SELECT * FROM INNODB_LOCK_WAITS
    """)
    waits = cursor.fetchall()
    if waits:
        for wait in waits:
            print(f'等待事务: {wait[0]}, 阻塞事务: {wait[1]}')
    else:
        print('没有锁等待')
    
    # 查看所有进程
    print('\n=== 所有进程 ===')
    cursor.execute('SHOW PROCESSLIST')
    processes = cursor.fetchall()
    
    print(f'{"ID":<6} {"User":<12} {"Host":<25} {"DB":<15} {"Command":<12} {"Time":<8} {"State":<30}')
    print('=' * 100)
    
    for proc in processes:
        pid, user, host, db, command, time, state, info = proc
        if time > 60 or command != 'Sleep':
            print(f'{pid:<6} {user:<12} {host:<25} {str(db):<15} {command:<12} {time:<8} {str(state):<30}')
    
    conn.close()
    
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
