#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 stock_cache.db 中的 stock_history 数据转换为 Qlib 格式
"""

import os
import sys
import sqlite3
import pandas as pd
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from stock_cache_db import StockCache

def convert_stock_history_to_qlib():
    """将 stock_history 数据转换为 Qlib 格式"""
    print("开始转换 stock_history 数据为 Qlib 格式...")
    
    # 初始化 SQLite 缓存
    print("初始化 SQLite 缓存...")
    cache = StockCache()
    print(f"SQLite 数据库路径: {cache.db_path}")
    
    # 直接连接 SQLite 数据库获取所有股票代码
    sqlite_conn = sqlite3.connect(cache.db_path)
    sqlite_conn.row_factory = sqlite3.Row
    
    # 获取所有唯一的股票代码
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT DISTINCT stock_code FROM stock_history")
    stock_codes = [row[0] for row in cursor.fetchall()]
    print(f"找到 {len(stock_codes)} 只股票")
    
    # 创建 Qlib 数据目录
    qlib_data_dir = Path(os.path.dirname(__file__), "qlib_data")
    qlib_data_dir.mkdir(exist_ok=True)
    print(f"Qlib 数据目录: {qlib_data_dir}")
    
    # 统计信息
    total_stocks = len(stock_codes)
    processed_stocks = 0
    failed_stocks = 0
    
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
            
            if not rows:
                print(f"[{i}/{total_stocks}] {stock_code} 没有历史数据")
                failed_stocks += 1
                continue
            
            # 转换为 DataFrame
            data = []
            for row in rows:
                data.append({
                    'date': row['date'],
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume']),
                    'amount': float(row['amount'])
                })
            
            df = pd.DataFrame(data)
            
            # 转换为 Qlib 格式
            # Qlib 格式要求:
            # - 日期列名为 'date'
            # - 其他列名为: open, high, low, close, volume, amount
            # - 日期格式为 YYYY-MM-DD
            # - 数据按日期排序
            
            # 确保日期格式正确
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            
            # 保存为 CSV 文件
            # Qlib 通常使用股票代码作为文件名
            # 转换股票代码格式，例如 sh600519 -> 600519.SH
            normalized_code = stock_code
            if normalized_code.startswith(('sh', 'sz', 'bj')):
                normalized_code = normalized_code[2:]
            
            # 确定交易所后缀
            if normalized_code.startswith('6'):
                # 沪市股票
                qlib_code = f"{normalized_code}.SH"
            else:
                # 深市股票
                qlib_code = f"{normalized_code}.SZ"
            
            csv_path = qlib_data_dir / f"{qlib_code}.csv"
            
            # 保存 CSV 文件，使用逗号分隔，无索引
            df.to_csv(csv_path, index=False, sep=',')
            
            processed_stocks += 1
            print(f"[{i}/{total_stocks}] {stock_code} → {qlib_code} 转换成功: {len(df)} 条数据")
            
        except Exception as e:
            print(f"[{i}/{total_stocks}] 处理 {stock_code} 时出错: {e}")
            failed_stocks += 1
            continue
    
    # 关闭连接
    cursor.close()
    sqlite_conn.close()
    
    # 打印统计结果
    print("\n" + "="*70)
    print("转换结果统计")
    print(f"总股票数: {total_stocks}")
    print(f"成功转换: {processed_stocks}")
    print(f"失败: {failed_stocks}")
    print(f"成功率: {(processed_stocks / total_stocks * 100):.2f}%")
    print(f"Qlib 数据保存位置: {qlib_data_dir}")
    print("="*70)
    
    print("\nstock_history 数据转换为 Qlib 格式完成")

if __name__ == '__main__':
    convert_stock_history_to_qlib()
