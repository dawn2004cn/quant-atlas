#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试换手率数据获取
"""
from stock_cache_db import StockCache
from stock_async_fetcher import StockAsyncFetcher

# 测试股票代码
test_codes = ['600519', '600036', '601318']

print("测试换手率数据获取...")
print("=" * 60)

# 获取新数据
print("1. 获取新数据...")
fetcher = StockAsyncFetcher()
fetcher.fetch_and_cache(test_codes)
fetcher.close()

# 检查缓存中的数据
print("2. 检查缓存数据...")
cache = StockCache()

for code in test_codes:
    stock = cache.get_stock(code)
    if stock:
        print(f"{stock['code']} - {stock['name']}")
        print(f"   价格: ¥{stock['price']:.2f}")
        print(f"   涨跌: {stock['change_pct']:+.2f}%")
        print(f"   换手率: {stock.get('turnover', 0):.2f}%")
        print(f"   数据来源: {stock.get('data_source', 'unknown')}")
    else:
        print(f"{code} - 未找到数据")
    print("-" * 40)

cache.close()
print("测试完成！")
