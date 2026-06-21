#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API端点
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests


def test_market_movements_api():
    """测试市场异动API"""
    print("=== 测试市场异动API ===")
    
    try:
        # 直接调用API端点
        url = 'http://localhost:5000/api/market/movements'
        response = requests.get(url)
        print(f"API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"状态: {data.get('status')}")
            print(f"数据源: {data.get('data_source')}")
            print(f"数据数量: {len(data.get('data', []))}")
            
            if data.get('data'):
                print("\nAPI返回的市场异动数据:")
                for i, movement in enumerate(data['data'][:3]):
                    print(f"\n{ i+1 }. 股票: {movement.get('name', '未知')} ({movement.get('code', '未知')})")
                    print(f"   类型: {movement.get('type', '未知')}")
                    print(f"   时间: {movement.get('time', '未知')}")
                    print(f"   涨幅: {movement.get('change', '未知')}")
        else:
            print(f"API请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"测试市场异动API失败: {e}")


def test_market_rankings_api():
    """测试市场排行榜API"""
    print("\n=== 测试市场排行榜API ===")
    
    try:
        # 直接调用API端点
        url = 'http://localhost:5000/api/market-rankings'
        response = requests.get(url)
        print(f"API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"状态: {data.get('status')}")
            print(f"数据源: {data.get('data_source')}")
            
            if data.get('data'):
                rankings = data['data']
                print(f"涨幅榜数量: {len(rankings.get('gainers', []))}")
                print(f"跌幅榜数量: {len(rankings.get('losers', []))}")
                print(f"成交额榜数量: {len(rankings.get('amounts', []))}")
                print(f"换手率榜数量: {len(rankings.get('turnovers', []))}")
                
                if rankings.get('gainers'):
                    print("\n涨幅榜前3名:")
                    for i, stock in enumerate(rankings['gainers'][:3]):
                        print(f"{i+1}. {stock['name']} ({stock['code']}): {stock['change_pct']:.2f}%")
        else:
            print(f"API请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"测试市场排行榜API失败: {e}")


if __name__ == "__main__":
    print("开始测试API端点...")
    
    # 测试市场异动API
    test_market_movements_api()
    
    # 测试市场排行榜API
    test_market_rankings_api()
    
    print("\n测试完成!")
