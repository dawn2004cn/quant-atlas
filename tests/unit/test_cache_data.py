#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试缓存数据的正确性
"""

from stock_cache_db import StockCache
from datetime import datetime, timedelta


def test_cache_data():
    """测试缓存数据的正确性"""
    print("=" * 60)
    print("测试缓存数据的正确性")
    print("=" * 60)
    
    # 测试股票：601318 中国平安
    code = '601318'
    
    # 计算日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # 从缓存获取数据
    print(f"\n从缓存获取 {code} 从 {start_date} 到 {end_date} 的数据...")
    cache = StockCache()
    history_data = cache.get_stock_history(code, start_date, end_date)
    cache.close()
    
    if history_data and len(history_data) > 0:
        print(f"成功获取 {len(history_data)} 天数据")
        print("\n数据前10行:")
        print("日期\t\t开盘\t最高\t最低\t收盘")
        print("=" * 60)
        
        # 检查数据
        problematic_days = 0
        for i, data in enumerate(history_data[:10]):
            date = data['date']
            open_price = data['open']
            high_price = data['high']
            low_price = data['low']
            close_price = data['close']
            
            # 检查最高价和最低价的合理性
            if high_price < max(open_price, close_price):
                print(f"错误 {date}: 最高价 {high_price:.2f} 小于开盘或收盘价")
                problematic_days += 1
            if low_price > min(open_price, close_price):
                print(f"错误 {date}: 最低价 {low_price:.2f} 大于开盘或收盘价")
                problematic_days += 1
            
            # 打印数据
            print(f"{date}\t{open_price:.2f}\t{high_price:.2f}\t{low_price:.2f}\t{close_price:.2f}")
        
        # 检查所有数据
        print("\n检查所有数据:")
        for data in history_data:
            date = data['date']
            open_price = data['open']
            high_price = data['high']
            low_price = data['low']
            close_price = data['close']
            
            if high_price < max(open_price, close_price):
                problematic_days += 1
                print(f"错误 {date}: 最高价 {high_price:.2f} 小于开盘({open_price:.2f})或收盘({close_price:.2f})")
            if low_price > min(open_price, close_price):
                problematic_days += 1
                print(f"错误 {date}: 最低价 {low_price:.2f} 大于开盘({open_price:.2f})或收盘({close_price:.2f})")
        
        print(f"\n总共有 {problematic_days} 天数据有问题")
    else:
        print("获取数据失败: 缓存中没有数据")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_cache_data()
