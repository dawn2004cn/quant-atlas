#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试缓存数据结构
"""
import sys
sys.path.append('.')

from cache_factory import CacheFactory

print("=== 测试缓存数据结构 ===")

# 获取缓存实例
cache = CacheFactory.get_cache()

# 测试市场异动数据
print("\n1. 测试市场异动数据结构:")
try:
    movements = cache.get_market_movements(limit=5)
    print(f"市场异动数据数量: {len(movements)}")
    
    if movements:
        print("\n第一条市场异动数据结构:")
        first_movement = movements[0]
        print(f"数据类型: {type(first_movement)}")
        print(f"包含的键: {list(first_movement.keys())}")
        print(f"示例数据: {first_movement}")
        
        # 验证前端需要的字段
        required_fields = ['code', 'name', 'type', 'time', 'change']
        for field in required_fields:
            if field in first_movement:
                print(f"✅ 包含字段: {field}")
            else:
                print(f"❌ 缺少字段: {field}")
    else:
        print("缓存中无市场异动数据")
except Exception as e:
    print(f"获取市场异动数据失败: {e}")

# 测试市场排行榜数据
print("\n2. 测试市场排行榜数据结构:")
try:
    from services.service_container import service_container
    market_service = service_container.get_market_service()
    rankings = market_service.get_market_rankings()
    
    if rankings.get('status') == 'success':
        data = rankings.get('data', {})
        print(f"排行榜数据结构: {list(data.keys())}")
        
        # 测试涨幅榜数据结构
        if 'gainers' in data and data['gainers']:
            print("\n涨幅榜第一条数据结构:")
            first_gainer = data['gainers'][0]
            print(f"数据类型: {type(first_gainer)}")
            print(f"包含的键: {list(first_gainer.keys())}")
            print(f"示例数据: {first_gainer}")
            
            # 验证前端需要的字段
            required_fields = ['code', 'name', 'change_pct']
            for field in required_fields:
                if field in first_gainer:
                    print(f"✅ 包含字段: {field}")
                else:
                    print(f"❌ 缺少字段: {field}")
        
        # 测试跌幅榜数据结构
        if 'losers' in data and data['losers']:
            print("\n跌幅榜第一条数据结构:")
            first_loser = data['losers'][0]
            print(f"数据类型: {type(first_loser)}")
            print(f"包含的键: {list(first_loser.keys())}")
        
        # 测试成交榜数据结构
        if 'amounts' in data and data['amounts']:
            print("\n成交榜第一条数据结构:")
            first_amount = data['amounts'][0]
            print(f"数据类型: {type(first_amount)}")
            print(f"包含的键: {list(first_amount.keys())}")
        
        # 测试换手榜数据结构
        if 'turnovers' in data and data['turnovers']:
            print("\n换手榜第一条数据结构:")
            first_turnover = data['turnovers'][0]
            print(f"数据类型: {type(first_turnover)}")
            print(f"包含的键: {list(first_turnover.keys())}")
    else:
        print(f"获取排行榜数据失败: {rankings.get('message')}")
except Exception as e:
    print(f"获取排行榜数据失败: {e}")

print("\n=== 测试完成 ===")
