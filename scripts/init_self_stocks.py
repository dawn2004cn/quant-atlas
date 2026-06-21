#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化自选股分组，将监控股票添加到默认分组中
"""
from stock_cache_db import StockCache

# 监控的核心股票
WATCHED_STOCKS = [
    # 高波动股票（新增）
    '600276',  # 恒瑞医药
    '601012',  # 隆基绿能
    '000858',  # 五粮液
    '601888',  # 中国中免
    # 原有优质股票（保留）
    '600036',  # 招商银行
    '601318',  # 中国平安
    '600519',  # 贵州茅台
    # 移除低波动电力股，保留1只代表
    '601985',  # 中国核电（代表）
]

def init_self_stocks():
    """将监控股票添加到自选股分组"""
    print("🔄 初始化自选股分组...")
    
    cache = StockCache()
    
    # 获取默认分组（自选股）的ID
    default_group_id = cache.get_default_group_id()
    print(f"✅ 默认分组ID: {default_group_id}")
    
    # 获取当前分组中的股票
    existing_stocks = cache.get_stocks_by_group(default_group_id)
    print(f"📊 当前自选股数量: {len(existing_stocks)}")
    
    # 添加监控股票到自选股分组
    added_count = 0
    for stock_code in WATCHED_STOCKS:
        if stock_code not in existing_stocks:
            success = cache.add_stock_to_group(stock_code, default_group_id)
            if success:
                added_count += 1
    
    cache.close()
    
    print(f"✅ 成功添加 {added_count} 只股票到自选股分组")
    print(f"✅ 自选股分组初始化完成，共 {len(existing_stocks) + added_count} 只股票")

if __name__ == '__main__':
    init_self_stocks()
