#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试缓存回退功能
"""
import pytest

pytest.skip("Legacy cache_factory tests", allow_module_level=True)

import json
from cache_factory import SmartCacheFactory
from market_sentiment import calculate_market_sentiment


def test_market_sentiment_cache():
    """测试市场情绪缓存功能"""
    print("测试市场情绪缓存功能...")
    
    # 计算市场情绪
    sentiment = calculate_market_sentiment(use_demo_data=False)
    print(f"市场情绪得分: {sentiment['score']}")
    print(f"市场情绪等级: {sentiment['level']}")
    
    # 保存到缓存
    cache = SmartCacheFactory.get_cache(data_type='market')
    success = cache.save_market_sentiment_cache(sentiment)
    print(f"保存市场情绪到缓存: {'成功' if success else '失败'}")
    
    # 从缓存读取
    cached_sentiment = cache.get_market_sentiment_cache()
    if cached_sentiment:
        print(f"从缓存读取市场情绪得分: {cached_sentiment['score']}")
        print(f"从缓存读取市场情绪等级: {cached_sentiment['level']}")
        return True
    else:
        print("从缓存读取市场情绪失败")
        return False


def test_market_movements_cache():
    """测试市场异动缓存功能"""
    print("\n测试市场异动缓存功能...")
    
    # 模拟市场异动数据
    movements = [
        {'code': '600519', 'name': '贵州茅台', 'type': '大幅上涨', 'change': '+5.2%', 'time': '2026-04-05 10:00:00'},
        {'code': '601318', 'name': '中国平安', 'type': '大幅下跌', 'change': '-3.1%', 'time': '2026-04-05 10:30:00'}
    ]
    
    # 保存到缓存
    cache = SmartCacheFactory.get_cache(data_type='market')
    success = cache.save_market_movements(movements)
    print(f"保存市场异动到缓存: {'成功' if success else '失败'}")
    
    # 从缓存读取
    cached_movements = cache.get_market_movements(limit=20)
    if cached_movements:
        print(f"从缓存读取市场异动数据数量: {len(cached_movements)}")
        for i, item in enumerate(cached_movements[:2]):
            print(f"  {i+1}. {item['name']} ({item['code']}): {item['type']} - {item['change']}")
        return True
    else:
        print("从缓存读取市场异动失败")
        return False


def test_historical_market_movements():
    """测试历史市场异动功能"""
    print("\n测试历史市场异动功能...")
    
    # 从缓存读取历史市场异动
    cache = SmartCacheFactory.get_cache(data_type='market')
    historical_movements = cache.get_historical_market_movements(limit=20)
    if historical_movements:
        print(f"从缓存读取历史市场异动数据数量: {len(historical_movements)}")
        for i, item in enumerate(historical_movements[:2]):
            print(f"  {i+1}. {item['name']} ({item['code']}): {item['type']} - {item['change']}")
        return True
    else:
        print("从缓存读取历史市场异动失败")
        return False


def main():
    """主测试函数"""
    print("开始测试缓存回退功能...\n")
    
    success_count = 0
    total_count = 3
    
    if test_market_sentiment_cache():
        success_count += 1
    
    if test_market_movements_cache():
        success_count += 1
    
    if test_historical_market_movements():
        success_count += 1
    
    print(f"\n测试结果: {success_count}/{total_count} 个测试通过")
    
    if success_count == total_count:
        print("所有缓存回退功能测试通过！")
    else:
        print("部分缓存回退功能测试失败，请检查日志了解详情。")


if __name__ == "__main__":
    main()
