#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试市场异动API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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


if __name__ == "__main__":
    print("开始测试市场异动...")
    test_market_movements()
    print("\n测试完成!")
