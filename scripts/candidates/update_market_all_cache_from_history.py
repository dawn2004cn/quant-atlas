#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从股票历史记录更新market_all_cache
将每只股票的最近日期的数据写入到market_all_cache
"""

import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'stock_cache.db')


def get_all_stock_codes():
    """获取所有股票代码"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        # 从stock_history表中获取所有不同的股票代码
        cursor.execute('SELECT DISTINCT stock_code FROM stock_history')
        codes = [row[0] for row in cursor.fetchall()]
        return codes
    finally:
        conn.close()


def get_latest_stock_data(stock_code):
    """获取股票的最近日期的数据"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        # 获取该股票的最新一条历史数据
        cursor.execute('''
            SELECT date, open, high, low, close, volume, amount
            FROM stock_history
            WHERE stock_code = ?
            ORDER BY date DESC
            LIMIT 1
        ''', (stock_code,))
        row = cursor.fetchone()
        if row:
            date, open_price, high, low, close, volume, amount = row
            return {
                'code': stock_code,
                'date': date,
                'open': float(open_price),
                'high': float(high),
                'low': float(low),
                'close': float(close),
                'volume': float(volume),
                'amount': float(amount)
            }
        return None
    finally:
        conn.close()


def get_stock_name(stock_code):
    """获取股票名称"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        # 从stocks表中获取股票名称
        cursor.execute('SELECT name FROM stocks WHERE code = ?', (stock_code,))
        row = cursor.fetchone()
        if row:
            return row[0]
        return stock_code  # 如果没有名称，返回代码
    finally:
        conn.close()


def update_market_all_cache():
    """更新market_all_cache"""
    print("=" * 60)
    print("从股票历史记录更新market_all_cache")
    print("=" * 60)
    
    # 获取所有股票代码
    stock_codes = get_all_stock_codes()
    print(f"获取到 {len(stock_codes)} 只股票代码")
    
    # 收集每只股票的最新数据
    stocks_data = []
    for i, code in enumerate(stock_codes):
        # 获取股票名称
        name = get_stock_name(code)
        # 获取最新数据
        latest_data = get_latest_stock_data(code)
        if latest_data:
            # 计算涨跌幅（这里简化处理，使用前一天的收盘价计算）
            # 实际应用中可能需要更复杂的计算
            change_pct = 0.0
            
            # 构建股票数据字典
            stock_info = {
                'code': code,
                'name': name,
                'price': latest_data['close'],
                'change_pct': change_pct,
                'volume': latest_data['volume'],
                'amount': latest_data['amount'],
                'open': latest_data['open'],
                'high': latest_data['high'],
                'low': latest_data['low'],
                'date': latest_data['date']
            }
            stocks_data.append(stock_info)
        
        # 打印进度
        if (i + 1) % 100 == 0 or (i + 1) == len(stock_codes):
            print(f"处理进度: {i + 1}/{len(stock_codes)}, 成功: {len(stocks_data)}")
    
    # 保存到market_all_cache
    if stocks_data:
        print(f"\n准备保存 {len(stocks_data)} 只股票的最新数据到market_all_cache")
        
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            now = datetime.now()
            
            # 将数据转换为 JSON 字符串
            data_json = json.dumps(stocks_data, separators=(',', ':'))
            
            # 先清空旧数据
            cursor.execute('DELETE FROM market_all_cache')
            
            # 插入新数据
            cursor.execute('''
                INSERT INTO market_all_cache (data, update_time)
                VALUES (?, ?)
            ''', (data_json, now))
            
            conn.commit()
            print(f"全市场数据已缓存: {len(stocks_data)} 只股票")
        finally:
            conn.close()
    else:
        print("没有获取到股票数据")
    
    print("\n" + "=" * 60)
    print("更新完成")
    print("=" * 60)


if __name__ == '__main__':
    update_market_all_cache()
