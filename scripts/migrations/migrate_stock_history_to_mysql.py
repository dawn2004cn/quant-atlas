#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 stock_cache.db 中的 stock_history 数据导入到 MySQL 的 stock_history 表中
"""

import os
import sys
import sqlite3
from typing import List, Dict

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.infrastructure.database.mysql_client import mysql_connect, ensure_mysql_schema
from app.infrastructure.database.mysql_settings import MysqlSettings

# 添加当前目录到路径，以便导入 stock_cache_db
sys.path.insert(0, os.path.dirname(__file__))
from stock_cache_db import StockCache

def migrate_stock_history_to_mysql():
    """将 stock_cache.db 中的 stock_history 数据导入到 MySQL"""
    print("开始迁移 stock_history 数据到 MySQL...")
    
    # 初始化 SQLite 缓存
    print("初始化 SQLite 缓存...")
    cache = StockCache()
    print("SQLite 缓存初始化完成")
    
    # 初始化 MySQL 连接
    print("初始化 MySQL 连接...")
    mysql_settings = MysqlSettings(
        host=os.environ.get("MYSQL_HOST", "192.168.8.103"),
        port=int(os.environ.get("MYSQL_PORT", "3307")),
        user=os.environ.get("MYSQL_USER", "admin"),
        password=os.environ.get("MYSQL_PASSWORD") or "",
        database=os.environ.get("MYSQL_DATABASE", "a_stock_monitor")
    )
    
    conn = mysql_connect(mysql_settings, autocommit=True)
    print(f"MySQL 连接成功: {mysql_settings.describe()}")
    
    # 确保 MySQL 表结构存在
    print("确保 MySQL 表结构存在...")
    ensure_mysql_schema(conn)
    print("MySQL 表结构检查完成")
    
    # 从 SQLite 读取 stock_history 数据
    print("从 SQLite 读取 stock_history 数据...")
    
    # 直接连接 SQLite 数据库获取所有股票代码
    sqlite_conn = sqlite3.connect(cache.db_path)
    sqlite_conn.row_factory = sqlite3.Row
    
    # 获取所有唯一的股票代码
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT DISTINCT stock_code FROM stock_history")
    stock_codes = [row[0] for row in cursor.fetchall()]
    print(f"找到 {len(stock_codes)} 只股票")
    
    # 统计信息
    total_records = 0
    successfully_inserted = 0
    failed_records = 0
    
    # 批量插入数据
    batch_size = 1000
    
    for i, stock_code in enumerate(stock_codes, 1):
        try:
            # 读取该股票的历史数据
            cursor.execute("""
                SELECT stock_code, date, open, high, low, close, volume, amount 
                FROM stock_history 
                WHERE stock_code = ? 
                ORDER BY date
            """, (stock_code,))
            
            rows = cursor.fetchall()
            total_records += len(rows)
            
            if not rows:
                print(f"[{i}/{len(stock_codes)}] {stock_code} 没有历史数据")
                continue
            
            # 批量插入到 MySQL
            mysql_cursor = conn.cursor()
            
            # 准备批量插入数据
            data = []
            for row in rows:
                data.append((
                    row['stock_code'],
                    row['date'],
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume']),
                    float(row['amount'])
                ))
            
            # 执行批量插入
            sql = """
                INSERT IGNORE INTO stock_history 
                (stock_code, date, open, high, low, close, volume, amount) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # 分批插入
            for j in range(0, len(data), batch_size):
                batch = data[j:j+batch_size]
                mysql_cursor.executemany(sql, batch)
                conn.commit()
            
            successfully_inserted += len(rows)
            print(f"[{i}/{len(stock_codes)}] {stock_code} 导入成功: {len(rows)} 条数据")
            
        except Exception as e:
            print(f"[{i}/{len(stock_codes)}] 处理 {stock_code} 时出错: {e}")
            failed_records += len(rows) if 'rows' in locals() else 0
            continue
    
    # 关闭连接
    cursor.close()
    sqlite_conn.close()
    conn.close()
    
    # 打印统计结果
    print("\n" + "="*70)
    print("迁移结果统计")
    print(f"总记录数: {total_records}")
    print(f"成功导入: {successfully_inserted}")
    print(f"失败: {failed_records}")
    print(f"成功率: {(successfully_inserted / total_records * 100):.2f}%")
    print("="*70)
    
    print("\nstock_history 数据迁移完成")

if __name__ == '__main__':
    migrate_stock_history_to_mysql()
