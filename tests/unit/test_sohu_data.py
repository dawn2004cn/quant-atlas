#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试搜狐接口数据的正确性
"""

from data_fetchers import fetch_from_sohu
from datetime import datetime, timedelta


def test_sohu_data():
    """测试搜狐接口数据的正确性"""
    print("=" * 60)
    print("测试搜狐接口数据的正确性")
    print("=" * 60)
    
    # 测试股票：601318 中国平安
    code = '601318'
    
    # 计算日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # 从搜狐接口获取数据
    print(f"\n从搜狐接口获取 {code} 从 {start_date} 到 {end_date} 的数据...")
    df, error = fetch_from_sohu(code, start_date, end_date)
    
    if df is not None and not df.empty:
        print(f"成功获取 {len(df)} 天数据")
        print("\n数据前10行:")
        print("日期\t\t开盘\t最高\t最低\t收盘")
        print("=" * 60)
        
        # 检查数据
        for i, (date, row) in enumerate(df.iterrows()):
            if i >= 10:
                break
            
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            
            # 检查最高价和最低价的合理性
            if high_price < max(open_price, close_price):
                print(f"错误 {date.date()}: 最高价 {high_price:.2f} 小于开盘或收盘价")
            if low_price > min(open_price, close_price):
                print(f"错误 {date.date()}: 最低价 {low_price:.2f} 大于开盘或收盘价")
            
            # 打印数据
            print(f"{date.date()}\t{open_price:.2f}\t{high_price:.2f}\t{low_price:.2f}\t{close_price:.2f}")
        
        # 检查所有数据
        print("\n检查所有数据:")
        problematic_days = 0
        for date, row in df.iterrows():
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            
            if high_price < max(open_price, close_price):
                problematic_days += 1
                print(f"错误 {date.date()}: 最高价 {high_price:.2f} 小于开盘({open_price:.2f})或收盘({close_price:.2f})")
            if low_price > min(open_price, close_price):
                problematic_days += 1
                print(f"错误 {date.date()}: 最低价 {low_price:.2f} 大于开盘({open_price:.2f})或收盘({close_price:.2f})")
        
        print(f"\n总共有 {problematic_days} 天数据有问题")
    else:
        print(f"获取数据失败: {error}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_sohu_data()
