#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 MySQL 查询速度"""

import time
import sys
from pathlib import Path

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from dotenv import load_dotenv
load_dotenv()

from app.config import get_settings

settings = get_settings()
ms = settings.mysql
print(f"MySQL host: {ms.host}")
print(f"MySQL database: {ms.database}")

import pymysql

conn = pymysql.connect(
    host=ms.host,
    port=ms.port,
    user=ms.user,
    password=ms.password,
    database=ms.database,
    charset="utf8mb4",
    read_timeout=300,
    write_timeout=300,
)

try:
    # 测试1: 获取日期范围
    print("\n测试1: 获取日期范围 (MIN/MAX)...")
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute("SELECT MIN(date), MAX(date), COUNT(*) FROM stock_history_sh")
        min_sh, max_sh, count_sh = cur.fetchone()
        cur.execute("SELECT MIN(date), MAX(date), COUNT(*) FROM stock_history_sz")
        min_sz, max_sz, count_sz = cur.fetchone()
        cur.execute("SELECT MIN(date), MAX(date), COUNT(*) FROM stock_history_bj")
        min_bj, max_bj, count_bj = cur.fetchone()
    t1 = time.time()
    print(f"  时间: {t1-t0:.2f}秒")
    print(f"  sh: {min_sh} - {max_sh} ({count_sh} rows)")
    print(f"  sz: {min_sz} - {max_sz} ({count_sz} rows)")
    print(f"  bj: {min_bj} - {max_bj} ({count_bj} rows)")

    # 测试2: 按表分别获取不同日期
    print("\n测试2: 分别获取每表的不同日期...")
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT date FROM stock_history_sh ORDER BY date ASC")
        dates_sh = [str(row[0]) for row in cur.fetchall() if row[0]]
        print(f"  sh: {len(dates_sh)} dates")

        cur.execute("SELECT DISTINCT date FROM stock_history_sz ORDER BY date ASC")
        dates_sz = [str(row[0]) for row in cur.fetchall() if row[0]]
        print(f"  sz: {len(dates_sz)} dates")

        cur.execute("SELECT DISTINCT date FROM stock_history_bj ORDER BY date ASC")
        dates_bj = [str(row[0]) for row in cur.fetchall() if row[0]]
        print(f"  bj: {len(dates_bj)} dates")
    t1 = time.time()
    print(f"  总时间: {t1-t0:.2f}秒")

    # 合并所有日期
    all_dates = sorted(set(dates_sh) | set(dates_sz) | set(dates_bj))
    print(f"  合并后: {len(all_dates)} dates")
    print(f"  前10个: {all_dates[:10]}")
    print(f"  后10个: {all_dates[-10:]}")

    # 测试3: 原始UNION查询
    print("\n测试3: UNION查询（原始方式）...")
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT date FROM stock_history_sh
            UNION SELECT DISTINCT date FROM stock_history_sz
            UNION SELECT DISTINCT date FROM stock_history_bj
            ORDER BY date ASC
        """)
        dates_union = [str(row[0]) for row in cur.fetchall() if row[0]]
    t1 = time.time()
    print(f"  时间: {t1-t0:.2f}秒")
    print(f"  日期数: {len(dates_union)}")

    print("\n✅ 所有测试完成!")

finally:
    conn.close()
