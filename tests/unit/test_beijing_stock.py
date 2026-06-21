#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试北交所股票数据获取
"""
import pandas as pd
from datetime import datetime
from data_fetchers import (
    fetch_from_yfinance, fetch_from_tencent, 
    fetch_from_sohu, fetch_from_adata,
    ADATA_AVAILABLE
)

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
]

# 测试时间范围
START_DATE = '2025-01-01'
END_DATE = datetime.today().strftime('%Y-%m-%d')

def test_data_fetcher(fetcher_func, stock_code, fetcher_name):
    """
    测试单个数据获取器
    """
    print(f"\n测试 {fetcher_name} 获取北交所股票 {stock_code} 数据...")
    try:
        df, error = fetcher_func(stock_code, START_DATE, END_DATE)
        if df is not None and not df.empty:
            print(f"[OK] {fetcher_name} 成功获取数据，形状: {df.shape}")
            print(f"  数据范围: {df.index.min()} 到 {df.index.max()}")
            print(f"  最新数据: {df.iloc[-1].to_dict()}")
            return True
        else:
            print(f"[FAIL] {fetcher_name} 失败: {error}")
            return False
    except Exception as e:
        print(f"[ERROR] {fetcher_name} 异常: {str(e)}")
        return False

def main():
    """
    主测试函数
    """
    print("=" * 80)
    print("测试北交所股票数据获取接口")
    print(f"测试时间范围: {START_DATE} 到 {END_DATE}")
    print("=" * 80)
    
    # 测试每个北交所股票
    for stock_code in BEIJING_STOCKS:
        print(f"\n" + "-" * 60)
        print(f"测试股票: {stock_code}")
        print("-" * 60)
        
        # 测试各个数据源
        success_count = 0
        
        # 测试 Yahoo Finance
        if test_data_fetcher(fetch_from_yfinance, stock_code, "Yahoo Finance"):
            success_count += 1
        
        # 测试 腾讯
        if test_data_fetcher(fetch_from_tencent, stock_code, "腾讯"):
            success_count += 1
        
        # 测试 搜狐
        if test_data_fetcher(fetch_from_sohu, stock_code, "搜狐"):
            success_count += 1
        
        # 测试 adata
        if ADATA_AVAILABLE:
            if test_data_fetcher(fetch_from_adata, stock_code, "adata"):
                success_count += 1
        else:
            print("[SKIP] adata 库未安装，跳过测试")
        
        print(f"\n股票 {stock_code} 测试结果: {success_count}/4 个接口成功")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
