#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""终止MySQL阻塞进程"""

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
        database='mysql',
        connect_timeout=30
    )
    cursor = conn.cursor()
    
    cursor.execute('SHOW PROCESSLIST')
    processes = cursor.fetchall()
    
    print('\n当前进程列表:')
    print('=' * 80)
    print(f'{"ID":<6} {"User":<12} {"Host":<20} {"DB":<15} {"Command":<12} {"Time":<8} {"State":<20}')
    print('=' * 80)
    
    blocking_pids = []
    for proc in processes:
        pid, user, host, db, command, time, state, info = proc
        if command == 'Sleep' and time > 60:
            blocking_pids.append(pid)
        print(f'{pid:<6} {user:<12} {host:<20} {str(db):<15} {command:<12} {time:<8} {str(state):<20}')
    
    if blocking_pids:
        print(f'\n终止阻塞进程: {blocking_pids}')
        for pid in blocking_pids:
            try:
                cursor.execute(f'KILL {pid}')
                print(f'已终止进程 {pid}')
            except Exception as e:
                print(f'终止进程 {pid} 失败: {e}')
    
    conn.commit()
    conn.close()
    print('\n操作完成!')
    
except Exception as e:
    print(f'错误: {e}')
