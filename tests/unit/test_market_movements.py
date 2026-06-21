#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试市场异动数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cache_factory import CacheFactory


def test_market_movements_cache():
    """测试市场异动缓存"""
    print("=== 测试市场异动缓存 ===")
    
    try:
        cache = CacheFactory.get_cache()
        
        # 获取市场异动数据
        cached_movements = cache.get_market_movements(limit=20)
        
        if cached_movements:
            print(f"✅ 市场异动缓存存在，数量: {len(cached_movements)}")
            print("\n缓存中的市场异动数据:")
            
            for i, movement in enumerate(cached_movements):
                print(f"\n{ i+1 }. 股票: {movement.get('name', '未知')} ({movement.get('code', '未知')})")
                print(f"   类型: {movement.get('type', '未知')}")
                print(f"   时间: {movement.get('time', '未知')}")
                print(f"   涨幅: {movement.get('change', '未知')}")
                print(f"   数据结构: {list(movement.keys())}")
        else:
            print("❌ 市场异动缓存不存在")
            
    except Exception as e:
        print(f"测试市场异动缓存失败: {e}")


def test_cache_keys():
    """测试缓存中的键"""
    print("\n=== 测试缓存键 ===")
    
    try:
        cache = CacheFactory.get_cache()
        
        # 尝试获取所有键（如果缓存支持）
        if hasattr(cache, 'get_all_keys'):
            keys = cache.get_all_keys()
            print(f"缓存中的键数量: {len(keys)}")
            print("前10个键:")
            for key in keys[:10]:
                print(f"  - {key}")
        else:
            print("缓存不支持获取所有键")
            
    except Exception as e:
        print(f"测试缓存键失败: {e}")


if __name__ == "__main__":
    print("开始测试市场异动数据...")
    
    # 测试市场异动缓存
    test_market_movements_cache()
    
    # 测试缓存键
    test_cache_keys()
    
    print("\n测试完成!")
