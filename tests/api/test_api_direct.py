#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试API端点
"""
import pytest

pytest.skip("Legacy services.market_service tests", allow_module_level=True)

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_service import MarketService
from cache_factory import CacheFactory


def test_market_movements():
    """测试市场异动"""
    print("=== 测试市场异动 ===")
    
    try:
        # 测试缓存中的市场异动数据
        cache = CacheFactory.get_cache()
        cached_movements = cache.get_market_movements(limit=20)
        
        if cached_movements:
            print(f"✅ 缓存中的市场异动数据数量: {len(cached_movements)}")
            print("\n缓存数据示例:")
            for i, movement in enumerate(cached_movements[:3]):
                print(f"{i+1}. {movement['name']} ({movement['code']}): {movement['type']} - {movement['change']}")
        else:
            print("❌ 缓存中没有市场异动数据")
            
    except Exception as e:
        print(f"测试市场异动失败: {e}")


def test_market_rankings():
    """测试市场排行榜"""
    print("\n=== 测试市场排行榜 ===")
    market_service = MarketService()
    result = market_service.get_market_rankings()
    print(f"状态: {result.get('status')}")
    print(f"数据源: {result.get('data_source')}")
    if result.get('data'):
        data = result['data']
        print(f"涨幅榜数量: {len(data.get('gainers', []))}")
        print(f"跌幅榜数量: {len(data.get('losers', []))}")
        print(f"成交额榜数量: {len(data.get('amounts', []))}")
        print(f"换手率榜数量: {len(data.get('turnovers', []))}")
        if data.get('gainers'):
            print("\n涨幅榜前3名:")
            for i, stock in enumerate(data['gainers'][:3]):
                print(f"{i+1}. {stock['name']} ({stock['code']}): {stock['change_pct']:.2f}%")


def test_market_all():
    """测试全市场数据"""
    print("\n=== 测试全市场数据 ===")
    market_service = MarketService()
    result = market_service.get_market_all()
    print(f"状态: {result.get('status')}")
    print(f"数据源: {result.get('data_source')}")
    if result.get('data'):
        print(f"数据数量: {len(result['data'])}")


if __name__ == "__main__":
    print("开始测试API...")
    test_market_movements()
    test_market_rankings()
    test_market_all()
    print("\n测试完成!")
