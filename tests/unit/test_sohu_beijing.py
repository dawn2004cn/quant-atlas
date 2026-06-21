#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试搜狐接口获取北交所股票数据
"""
import pandas as pd
from datetime import datetime
from data_fetchers import fetch_from_sohu

# 测试的北交所股票代码
BEIJING_STOCKS = [
    '830832',  # 齐鲁华信
    '831832',  # 科润智控
    '832185',  # 华维设计
    '832885',  # 星辰科技
    '833873',  # 星辰科技
    '834682',  # 球冠电缆
    '835185',  # 贝特瑞
    '835368',  # 连城数控
    '836239',  # 长虹能源
    '836720',  # 吉冈精密
    '920011',  # 吉冈精密
]

# 测试时间范围
START_DATE = '2025-01-01'
END_DATE = datetime.today().strftime('%Y-%m-%d')

def test_sohu_fetcher(stock_code):
    """
    测试搜狐接口获取北交所股票数据
    """
    print(f"\n测试搜狐接口获取北交所股票 {stock_code} 数据...")
    try:
        df, error = fetch_from_sohu(stock_code, START_DATE, END_DATE)
        if df is not None and not df.empty:
            print(f"[OK] 成功获取数据，形状: {df.shape}")
            print(f"  数据范围: {df.index.min()} 到 {df.index.max()}")
            print(f"  最新数据: {df.iloc[-1].to_dict()}")
            return True
        else:
            print(f"[FAIL] 失败: {error}")
            return False
    except Exception as e:
        print(f"[ERROR] 异常: {str(e)}")
        return False

def main():
    """
    主测试函数
    """
    print("=" * 80)
    print("测试搜狐接口获取北交所股票数据")
    print(f"测试时间范围: {START_DATE} 到 {END_DATE}")
    print("=" * 80)
    
    # 测试每个北交所股票
    success_count = 0
    total_count = len(BEIJING_STOCKS)
    
    for stock_code in BEIJING_STOCKS:
        if test_sohu_fetcher(stock_code):
            success_count += 1
    
    print(f"\n" + "=" * 80)
    print(f"测试完成: {success_count}/{total_count} 个股票成功")
    print("=" * 80)

if __name__ == "__main__":
    main()
