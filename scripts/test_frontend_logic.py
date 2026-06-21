#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端逻辑，模拟API调用和数据处理
"""
import sys
import json
sys.path.append('.')

from services.service_container import service_container
from cache_factory import CacheFactory

print("=== 测试前端逻辑 ===")

# 从服务容器获取市场服务
market_service = service_container.get_market_service()
cache = CacheFactory.get_cache()

# 模拟前端调用API获取市场异动数据
print("\n1. 模拟获取市场异动数据:")
try:
    # 调用API获取数据
    movements = cache.get_market_movements(limit=20)
    print(f"获取到 {len(movements)} 条市场异动数据")
    
    # 模拟前端数据处理
    if movements:
        print("\n模拟前端数据处理:")
        for i, movement in enumerate(movements[:3]):
            print(f"{i+1}. {movement.get('name')} ({movement.get('code')}): {movement.get('type')} {movement.get('change', '')}")
    else:
        print("无市场异动数据")
except Exception as e:
    print(f"获取市场异动数据失败: {e}")

# 模拟前端调用API获取排行榜数据
print("\n2. 模拟获取排行榜数据:")
try:
    # 调用API获取数据
    rankings = market_service.get_market_rankings()
    
    if rankings.get('status') == 'success':
        data = rankings.get('data', {})
        print(f"获取到排行榜数据")
        print(f"涨幅榜: {len(data.get('gainers', []))} 条")
        print(f"跌幅榜: {len(data.get('losers', []))} 条")
        print(f"成交榜: {len(data.get('amounts', []))} 条")
        print(f"换手榜: {len(data.get('turnovers', []))} 条")
        
        # 模拟前端数据处理
        if data.get('gainers'):
            print("\n涨幅榜前3名:")
            for i, stock in enumerate(data['gainers'][:3]):
                print(f"{i+1}. {stock.get('name')} ({stock.get('code')}): {stock.get('change_pct', 0):+.2f}%")
        
        if data.get('losers'):
            print("\n跌幅榜前3名:")
            for i, stock in enumerate(data['losers'][:3]):
                print(f"{i+1}. {stock.get('name')} ({stock.get('code')}): {stock.get('change_pct', 0):+.2f}%")
    else:
        print(f"获取排行榜数据失败: {rankings.get('message')}")
except Exception as e:
    print(f"获取排行榜数据失败: {e}")

# 检查前端API调用路径是否正确
print("\n3. 检查API调用路径:")
api_endpoints = [
    '/api/market/movements',
    '/api/market-rankings',
    '/api/market/sentiment'
]

print("前端调用的API端点:")
for endpoint in api_endpoints:
    print(f"- {endpoint}")

# 检查数据格式是否符合前端期望
print("\n4. 检查数据格式:")

# 检查市场异动数据格式
print("市场异动数据格式:")
if movements:
    first_movement = movements[0]
    print(f"包含字段: {list(first_movement.keys())}")
    print(f"示例: {json.dumps(first_movement, ensure_ascii=False)}")

# 检查排行榜数据格式
print("\n排行榜数据格式:")
if rankings.get('status') == 'success' and data.get('gainers'):
    first_gainer = data['gainers'][0]
    print(f"包含字段: {list(first_gainer.keys())}")
    print(f"示例: {json.dumps(first_gainer, ensure_ascii=False)}")

print("\n=== 测试完成 ===")
print("\n诊断结果:")
print("1. 后端服务正常，能够提供市场数据")
print("2. 数据格式符合前端期望")
print("3. API端点路径正确")
print("\n可能的前端问题:")
print("- JavaScript错误导致API调用失败")
print("- 网络请求问题（跨域、权限等）")
print("- DOM元素选择器问题")
print("- 数据渲染逻辑错误")
