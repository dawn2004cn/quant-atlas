#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 MySQL 连接是否正常
"""

import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.infrastructure.database.mysql_client import mysql_connect
from app.infrastructure.database.mysql_settings import MysqlSettings

def test_mysql_connection():
    """测试 MySQL 连接"""
    print("测试 MySQL 连接...")
    
    # 使用修改后的连接信息
    mysql_settings = MysqlSettings(
        host=os.environ.get("MYSQL_HOST", "192.168.8.103"),
        port=int(os.environ.get("MYSQL_PORT", "3307")),
        user=os.environ.get("MYSQL_USER", "admin"),
        password=os.environ.get("MYSQL_PASSWORD") or "",
        database=os.environ.get("MYSQL_DATABASE", "a_stock_monitor")
    )
    
    try:
        conn = mysql_connect(mysql_settings, autocommit=True)
        print(f"✅ MySQL 连接成功: {mysql_settings.describe()}")
        
        # 测试数据库操作
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"✅ 数据库查询成功: {result}")
        
        # 检查 stock_history 表是否存在
        cursor.execute("SHOW TABLES LIKE 'stock_history'")
        tables = cursor.fetchall()
        if tables:
            print("✅ stock_history 表存在")
        else:
            print("❌ stock_history 表不存在")
        
        cursor.close()
        conn.close()
        print("✅ 连接测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_mysql_connection()
