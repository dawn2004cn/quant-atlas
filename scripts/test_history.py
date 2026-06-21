#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试历史数据获取功能
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

print("测试历史数据获取功能...")

# 直接测试 akshare
days = 365
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')

print(f"直接使用 akshare 获取 600519 的历史数据...")
df = ak.stock_zh_a_hist(
    symbol='600519', 
    period="daily", 
    start_date=start_date, 
    end_date=end_date, 
    adjust=""
)

print(f"akshare 返回数据形状: {df.shape}")
print(f"akshare 返回列名: {list(df.columns)}")
print(f"前5行数据:")
print(df.head())

# 尝试处理数据
print("\n处理数据...")
try:
    # 重命名列
    df = df.rename(columns={
        '日期': 'date',
        '开盘': 'open',
        '最高': 'high',
        '最低': 'low',
        '收盘': 'close',
        '成交量': 'volume',
        '成交额': 'amount',
    })
    print("重命名列成功")
    
    # 转换日期格式
    df['date'] = pd.to_datetime(df['date'])
    print("转换日期格式成功")
    
    # 设置索引
    df.set_index('date', inplace=True)
    print("设置索引成功")
    
    # 按日期排序
    df = df.sort_index()
    print("排序成功")
    
    # 只保留需要的列
    df = df[['open', 'high', 'low', 'close', 'volume', 'amount']]
    print("保留需要的列成功")
    
    print(f"处理后的数据形状: {df.shape}")
    print(f"处理后的数据范围: {df.index.min().strftime('%Y-%m-%d')} 到 {df.index.max().strftime('%Y-%m-%d')}")
    
except Exception as e:
    print(f"处理数据时出错: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成！")
