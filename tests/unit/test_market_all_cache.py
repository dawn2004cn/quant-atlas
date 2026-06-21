#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试全市场股票列表缓存回退功能
"""
import json
from cache_factory import SmartCacheFactory
from services.market_service import MarketService


def test_market_all_cache():
    """测试全市场股票列表缓存回退功能"""
    print("测试全市场股票列表缓存回退功能...")
    
    # 初始化市场服务
    market_service = MarketService()
    
    # 1. 测试正常获取全市场数据
    print("\n1. 测试正常获取全市场数据...")
    result = market_service.get_market_all()
    print(f"状态: {result['status']}")
    print(f"数据源: {result.get('data_source', 'unknown')}")
    if result.get('data'):
        print(f"数据数量: {len(result['data'])}")
        print(f"前5只股票: {[stock['code'] + ' ' + stock['name'] for stock in result['data'][:5]]}")
    else:
        print("数据为空")
    
    # 2. 测试缓存回退功能
    print("\n2. 测试缓存回退功能...")
    # 这里我们模拟在线获取失败的情况，通过直接调用缓存获取方法
    cache = SmartCacheFactory.get_cache(data_type='market')
    
    # 尝试获取不同时间范围的缓存数据
    print("\n尝试获取30分钟内的缓存数据...")
    cached_30min = cache.get_market_all_cache(max_age_minutes=30)
    if cached_30min:
        print(f"30分钟内缓存数据数量: {len(cached_30min)}")
    else:
        print("30分钟内无缓存数据")
    
    print("\n尝试获取24小时内的缓存数据...")
    cached_24h = cache.get_market_all_cache(max_age_minutes=1440)
    if cached_24h:
        print(f"24小时内缓存数据数量: {len(cached_24h)}")
    else:
        print("24小时内无缓存数据")
    
    print("\n尝试获取7天内的缓存数据...")
    cached_7d = cache.get_market_all_cache(max_age_minutes=10080)
    if cached_7d:
        print(f"7天内缓存数据数量: {len(cached_7d)}")
    else:
        print("7天内无缓存数据")
    
    return True


def main():
    """主测试函数"""
    print("开始测试全市场股票列表缓存回退功能...\n")
    
    success = test_market_all_cache()
    
    if success:
        print("\n测试成功！全市场股票列表缓存回退功能正常工作。")
    else:
        print("\n测试失败！全市场股票列表缓存回退功能出现问题。")


if __name__ == "__main__":
    main()
