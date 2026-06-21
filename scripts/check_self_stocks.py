#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查自选股分组中的股票
"""
from stock_cache_db import StockCache

# 主页监控的核心股票
WATCHED_STOCKS = [
    '600276',  # 恒瑞医药
    '601012',  # 隆基绿能
    '000858',  # 五粮液
    '601888',  # 中国中免
    '600036',  # 招商银行
    '601318',  # 中国平安
    '600519',  # 贵州茅台
    '601985',  # 中国核电
]

def check_self_stocks():
    """检查自选股分组中的股票"""
    print("🔍 检查自选股分组...")
    
    cache = StockCache()
    
    # 获取默认分组（自选股）的ID
    default_group_id = cache.get_default_group_id()
    print(f"✅ 默认分组ID: {default_group_id}")
    
    # 获取当前分组中的股票
    existing_stocks = cache.get_stocks_by_group(default_group_id)
    print(f"📊 当前自选股数量: {len(existing_stocks)}")
    print(f"📋 自选股列表: {existing_stocks}")
    
    # 检查是否有遗漏的股票
    missing_stocks = []
    for stock_code in WATCHED_STOCKS:
        if stock_code not in existing_stocks:
            missing_stocks.append(stock_code)
    
    if missing_stocks:
        print(f"⚠️  缺失的股票: {missing_stocks}")
        # 添加缺失的股票
        for stock_code in missing_stocks:
            success = cache.add_stock_to_group(stock_code, default_group_id)
            if success:
                print(f"✅ 添加股票 {stock_code} 到分组")
    else:
        print("✅ 所有监控股票都已在自选股分组中")
    
    cache.close()

if __name__ == '__main__':
    check_self_stocks()
