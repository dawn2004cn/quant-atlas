#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite 到 MySQL 的全量数据迁移脚本。
"""

import os
import sqlite3
import pymysql
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

# 导入项目配置逻辑
import sys
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.config import AppSettings
from app.infrastructure.database.mysql_client import mysql_connect, ensure_mysql_schema

def migrate():
    settings = AppSettings.from_env()
    if settings.database_backend != "mysql" or not settings.mysql:
        print("错误：当前环境变量未配置为使用 MySQL，请检查 .env 文件中的 DATABASE_BACKEND=mysql")
        return

    print(f"🚀 开始迁移数据到 MySQL: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}")
    
    # 1. 建立 MySQL 连接并初始化结构
    m_conn = mysql_connect(settings.mysql, autocommit=True)
    try:
        ensure_mysql_schema(m_conn)
        print("✅ MySQL 表结构检查/初始化完成")
    except Exception as e:
        print(f"❌ 初始化 MySQL 结构失败: {e}")
        return

    # 2. 定义映射关系 (SQLite 文件 -> 表列表)
    # 根据项目结构，不同的数据散落在不同的 db 文件中
    instance_dir = Path(project_root) / "instance"
    mapping = {
        "app_state_sqlite.db": ["roles", "users", "watchlist", "stock_groups", "stock_group_items"],
        "stock_cache.db": ["stocks", "stock_history"],
        "news_archive.db": ["archived_news", "news_symbol_meta"],
        "quant_platform_v2_b.db": [
            "market_sentiment", "market_sentiment_daily", "longhu_daily", 
            "yanbao_items", "basic_data_meta", "cn_financial_stash",
            "signal_flag_pool", "investment_managers", "manager_nav", 
            "manager_trades", "manager_holdings_snap", "manager_positions_state",
            "user_race_account", "user_race_trades", "user_race_nav",
            "moments_posts", "moments_attachments", "moments_likes", "moments_comments"
        ],
    }

    # 为了兼容，也检查一些备用文件名
    fallback_dbs = ["quant_platform_v2.db", "quant_platform.db"]

    for db_name, tables in mapping.items():
        db_path = instance_dir / db_name
        
        # 如果主文件不存在，尝试备用文件
        if not db_path.exists() and db_name == "quant_platform_v2_b.db":
            for f_db in fallback_dbs:
                if (instance_dir / f_db).exists():
                    db_path = instance_dir / f_db
                    break
        
        if not db_path.exists():
            print(f"⚠️ 跳过文件 {db_name} (不存在)")
            continue

        print(f"\n项目: {db_name} -> MySQL")
        s_conn = sqlite3.connect(db_path)
        s_conn.row_factory = sqlite3.Row
        s_cur = s_conn.cursor()

        for table in tables:
            try:
                # 检查 SQLite 中是否存在该表
                s_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not s_cur.fetchone():
                    continue

                # 获取总行数
                s_cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                total_rows = s_cur.fetchone()[0]
                if total_rows == 0:
                    print(f"  - {table}: 无数据")
                    continue

                # 获取列名
                s_cur.execute(f"SELECT * FROM `{table}` LIMIT 1")
                first_row = s_cur.fetchone()
                if not first_row:
                    continue
                columns = first_row.keys()
                placeholders = ", ".join(["%s"] * len(columns))
                col_names = ", ".join([f"`{c}`" for c in columns])
                
                # 清理旧数据并准备插入
                with m_conn.cursor() as m_cur:
                    m_cur.execute("SET FOREIGN_KEY_CHECKS = 0")
                    m_cur.execute(f"TRUNCATE TABLE `{table}`")
                    m_cur.execute("SET FOREIGN_KEY_CHECKS = 1")

                # 分批读取并写入
                batch_size = 2000
                offset = 0
                while offset < total_rows:
                    s_cur.execute(f"SELECT * FROM `{table}` LIMIT {batch_size} OFFSET {offset}")
                    rows = s_cur.fetchall()
                    if not rows:
                        break
                    
                    with m_conn.cursor() as m_cur:
                        sql = f"INSERT INTO `{table}` ({col_names}) VALUES ({placeholders})"
                        data = [tuple(row) for row in rows]
                        m_cur.executemany(sql, data)
                    
                    offset += len(rows)
                    print(f"\r  - {table}: 进度 {offset}/{total_rows}", end="", flush=True)
                
                print(f"\n  - {table}: 成功迁移 {total_rows} 记录")
            except Exception as e:
                print(f"\n  - {table}: 迁移失败 - {e}")

        s_conn.close()

    m_conn.close()
    print("\n✨ 数据迁移任务完成！")

if __name__ == "__main__":
    migrate()
