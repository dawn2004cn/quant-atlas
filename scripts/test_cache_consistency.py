#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Redis和SQLite缓存的方法一致性
"""
import sys
sys.path.append('.')

from cache_factory import SmartCacheFactory
from datetime import datetime, timedelta

print("=== 测试缓存一致性 ===")

# 获取Redis缓存实例
print("\n1. 获取Redis缓存实例")
try:
    redis_cache = SmartCacheFactory.get_redis_cache()
    print("✅ Redis缓存初始化成功")
except Exception as e:
    print(f"❌ Redis缓存初始化失败: {e}")
    redis_cache = None

# 获取SQLite缓存实例
print("\n2. 获取SQLite缓存实例")
try:
    sqlite_cache = SmartCacheFactory.get_sqlite_cache()
    print("✅ SQLite缓存初始化成功")
except Exception as e:
    print(f"❌ SQLite缓存初始化失败: {e}")
    sqlite_cache = None

# 测试数据
test_stock = {
    'code': '600519',
    'name': '贵州茅台',
    'price': 1789.00,
    'change_pct': 2.50,
    'volume': 1250000,
    'amount': 2236250000,
    'turnover': 1.2
}

test_fund_flow = {
    'main_in': 100000000,
    'retail_in': 50000000,
    'main_ratio': 0.67
}

test_tech_indicators = {
    'ma5': 1750.0,
    'ma10': 1720.0,
    'ma20': 1680.0,
    'rsi': 65.0,
    'macd': 12.5,
    'dif': 15.0,
    'dea': 2.5
}

test_market_data = [
    {'code': '600519', 'name': '贵州茅台', 'price': 1789.00, 'change_pct': 2.50},
    {'code': '601318', 'name': '中国平安', 'price': 48.20, 'change_pct': 1.20},
    {'code': '600036', 'name': '招商银行', 'price': 36.80, 'change_pct': 0.90}
]

test_movements = [
    {'code': '600519', 'name': '贵州茅台', 'type': '涨停', 'change': '10.00%', 'time': datetime.now().isoformat()},
    {'code': '601318', 'name': '中国平安', 'type': '大幅上涨', 'change': '5.20%', 'time': datetime.now().isoformat()}
]

# 测试Redis缓存
if redis_cache:
    print("\n3. 测试Redis缓存方法")
    
    # 测试保存和获取股票数据
    print("\n3.1 测试保存和获取股票数据")
    redis_cache.save_stock(test_stock['code'], test_stock)
    stock = redis_cache.get_stock(test_stock['code'])
    if stock:
        print(f"✅ Redis: 获取股票数据成功 - {stock['name']}: ¥{stock['price']}")
    else:
        print("❌ Redis: 获取股票数据失败")
    
    # 测试保存和获取资金流数据
    print("\n3.2 测试保存和获取资金流数据")
    redis_cache.save_fund_flow(test_stock['code'], test_fund_flow)
    fund_flow = redis_cache.get_fund_flow(test_stock['code'])
    if fund_flow:
        print(f"✅ Redis: 获取资金流数据成功 - 主力流入: {fund_flow['main_in']}")
    else:
        print("❌ Redis: 获取资金流数据失败")
    
    # 测试保存和获取技术指标数据
    print("\n3.3 测试保存和获取技术指标数据")
    redis_cache.save_tech_indicators(test_stock['code'], test_tech_indicators)
    tech_indicators = redis_cache.get_tech_indicators(test_stock['code'])
    if tech_indicators:
        print(f"✅ Redis: 获取技术指标数据成功 - RSI: {tech_indicators['rsi']}")
    else:
        print("❌ Redis: 获取技术指标数据失败")
    
    # 测试保存和获取全市场数据
    print("\n3.4 测试保存和获取全市场数据")
    redis_cache.save_market_all_cache(test_market_data)
    market_data = redis_cache.get_market_all_cache()
    if market_data:
        print(f"✅ Redis: 获取全市场数据成功 - {len(market_data)} 只股票")
    else:
        print("❌ Redis: 获取全市场数据失败")
    
    # 测试保存和获取市场异动数据
    print("\n3.5 测试保存和获取市场异动数据")
    redis_cache.save_market_movements(test_movements)
    movements = redis_cache.get_market_movements()
    if movements:
        print(f"✅ Redis: 获取市场异动数据成功 - {len(movements)} 条")
    else:
        print("❌ Redis: 获取市场异动数据失败")
    
    # 测试获取缓存统计
    print("\n3.6 测试获取缓存统计")
    stats = redis_cache.get_cache_stats()
    print(f"✅ Redis: 缓存统计 - 股票数量: {stats.get('stock_count', 0)}")

# 测试SQLite缓存
if sqlite_cache:
    print("\n4. 测试SQLite缓存方法")
    
    # 测试保存和获取股票数据
    print("\n4.1 测试保存和获取股票数据")
    sqlite_cache.save_stock(test_stock['code'], test_stock)
    stock = sqlite_cache.get_stock(test_stock['code'])
    if stock:
        print(f"✅ SQLite: 获取股票数据成功 - {stock['name']}: ¥{stock['price']}")
    else:
        print("❌ SQLite: 获取股票数据失败")
    
    # 测试保存和获取资金流数据
    print("\n4.2 测试保存和获取资金流数据")
    sqlite_cache.save_fund_flow(test_stock['code'], test_fund_flow)
    fund_flow = sqlite_cache.get_fund_flow(test_stock['code'])
    if fund_flow:
        print(f"✅ SQLite: 获取资金流数据成功 - 主力流入: {fund_flow['main_in']}")
    else:
        print("❌ SQLite: 获取资金流数据失败")
    
    # 测试保存和获取技术指标数据
    print("\n4.3 测试保存和获取技术指标数据")
    sqlite_cache.save_tech_indicators(test_stock['code'], test_tech_indicators)
    tech_indicators = sqlite_cache.get_tech_indicators(test_stock['code'])
    if tech_indicators:
        print(f"✅ SQLite: 获取技术指标数据成功 - RSI: {tech_indicators['rsi']}")
    else:
        print("❌ SQLite: 获取技术指标数据失败")
    
    # 测试保存和获取全市场数据
    print("\n4.4 测试保存和获取全市场数据")
    sqlite_cache.save_market_all_cache(test_market_data)
    market_data = sqlite_cache.get_market_all_cache()
    if market_data:
        print(f"✅ SQLite: 获取全市场数据成功 - {len(market_data)} 只股票")
    else:
        print("❌ SQLite: 获取全市场数据失败")
    
    # 测试保存和获取市场异动数据
    print("\n4.5 测试保存和获取市场异动数据")
    sqlite_cache.save_market_movements(test_movements)
    movements = sqlite_cache.get_market_movements()
    if movements:
        print(f"✅ SQLite: 获取市场异动数据成功 - {len(movements)} 条")
    else:
        print("❌ SQLite: 获取市场异动数据失败")
    
    # 测试获取缓存统计
    print("\n4.6 测试获取缓存统计")
    stats = sqlite_cache.get_cache_stats()
    print(f"✅ SQLite: 缓存统计 - 股票数量: {stats.get('stock_count', 0)}")

# 测试方法一致性
print("\n5. 测试方法一致性")

# 检查方法是否存在
if redis_cache and sqlite_cache:
    # 检查股票相关方法
    print("\n5.1 检查股票相关方法")
    redis_has_save_stock = hasattr(redis_cache, 'save_stock')
    sqlite_has_save_stock = hasattr(sqlite_cache, 'save_stock')
    print(f"save_stock - Redis: {redis_has_save_stock}, SQLite: {sqlite_has_save_stock}")
    
    redis_has_get_stock = hasattr(redis_cache, 'get_stock')
    sqlite_has_get_stock = hasattr(sqlite_cache, 'get_stock')
    print(f"get_stock - Redis: {redis_has_get_stock}, SQLite: {sqlite_has_get_stock}")
    
    # 检查资金流相关方法
    print("\n5.2 检查资金流相关方法")
    redis_has_save_fund_flow = hasattr(redis_cache, 'save_fund_flow')
    sqlite_has_save_fund_flow = hasattr(sqlite_cache, 'save_fund_flow')
    print(f"save_fund_flow - Redis: {redis_has_save_fund_flow}, SQLite: {sqlite_has_save_fund_flow}")
    
    redis_has_get_fund_flow = hasattr(redis_cache, 'get_fund_flow')
    sqlite_has_get_fund_flow = hasattr(sqlite_cache, 'get_fund_flow')
    print(f"get_fund_flow - Redis: {redis_has_get_fund_flow}, SQLite: {sqlite_has_get_fund_flow}")
    
    # 检查技术指标相关方法
    print("\n5.3 检查技术指标相关方法")
    redis_has_save_tech_indicators = hasattr(redis_cache, 'save_tech_indicators')
    sqlite_has_save_tech_indicators = hasattr(sqlite_cache, 'save_tech_indicators')
    print(f"save_tech_indicators - Redis: {redis_has_save_tech_indicators}, SQLite: {sqlite_has_save_tech_indicators}")
    
    redis_has_get_tech_indicators = hasattr(redis_cache, 'get_tech_indicators')
    sqlite_has_get_tech_indicators = hasattr(sqlite_cache, 'get_tech_indicators')
    print(f"get_tech_indicators - Redis: {redis_has_get_tech_indicators}, SQLite: {sqlite_has_get_tech_indicators}")
    
    # 检查市场数据相关方法
    print("\n5.4 检查市场数据相关方法")
    redis_has_save_market_all_cache = hasattr(redis_cache, 'save_market_all_cache')
    sqlite_has_save_market_all_cache = hasattr(sqlite_cache, 'save_market_all_cache')
    print(f"save_market_all_cache - Redis: {redis_has_save_market_all_cache}, SQLite: {sqlite_has_save_market_all_cache}")
    
    redis_has_get_market_all_cache = hasattr(redis_cache, 'get_market_all_cache')
    sqlite_has_get_market_all_cache = hasattr(sqlite_cache, 'get_market_all_cache')
    print(f"get_market_all_cache - Redis: {redis_has_get_market_all_cache}, SQLite: {sqlite_has_get_market_all_cache}")
    
    # 检查市场异动相关方法
    print("\n5.5 检查市场异动相关方法")
    redis_has_save_market_movements = hasattr(redis_cache, 'save_market_movements')
    sqlite_has_save_market_movements = hasattr(sqlite_cache, 'save_market_movements')
    print(f"save_market_movements - Redis: {redis_has_save_market_movements}, SQLite: {sqlite_has_save_market_movements}")
    
    redis_has_get_market_movements = hasattr(redis_cache, 'get_market_movements')
    sqlite_has_get_market_movements = hasattr(sqlite_cache, 'get_market_movements')
    print(f"get_market_movements - Redis: {redis_has_get_market_movements}, SQLite: {sqlite_has_get_market_movements}")
    
    # 检查其他方法
    print("\n5.6 检查其他方法")
    redis_has_get_cache_stats = hasattr(redis_cache, 'get_cache_stats')
    sqlite_has_get_cache_stats = hasattr(sqlite_cache, 'get_cache_stats')
    print(f"get_cache_stats - Redis: {redis_has_get_cache_stats}, SQLite: {sqlite_has_get_cache_stats}")
    
    redis_has_close = hasattr(redis_cache, 'close')
    sqlite_has_close = hasattr(sqlite_cache, 'close')
    print(f"close - Redis: {redis_has_close}, SQLite: {sqlite_has_close}")

# 关闭缓存连接
if redis_cache:
    redis_cache.close()
if sqlite_cache:
    sqlite_cache.close()

print("\n=== 测试完成 ===")
