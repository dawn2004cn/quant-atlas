#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试前端API调用
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json


def test_api_endpoints():
    """测试前端API端点"""
    print("=== 测试前端API端点 ===")
    
    try:
        # 创建session
        session = requests.Session()
        
        # 登录
        login_url = 'http://localhost:5000/login'
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        # 提交登录
        response = session.post(login_url, data=login_data)
        print(f"登录状态: {response.status_code}")
        
        if response.status_code == 302:  # 登录成功，重定向到首页
            print("✅ 登录成功")
            
            # 测试市场异动API
            print("\n=== 测试市场异动API ===")
            movements_url = 'http://localhost:5000/api/market/movements'
            movements_response = session.get(movements_url)
            print(f"API响应状态: {movements_response.status_code}")
            
            if movements_response.status_code == 200:
                try:
                    data = movements_response.json()
                    print(f"状态: {data.get('status')}")
                    print(f"数据源: {data.get('data_source')}")
                    print(f"数据数量: {len(data.get('data', []))}")
                    if data.get('data'):
                        print("\n市场异动数据示例:")
                        for i, movement in enumerate(data['data'][:3]):
                            print(f"{i+1}. {movement['name']} ({movement['code']}): {movement['type']} - {movement['change']}")
                except Exception as e:
                    print(f"解析JSON失败: {e}")
                    print(f"响应内容: {movements_response.text}")
            
            # 测试市场排行榜API
            print("\n=== 测试市场排行榜API ===")
            rankings_url = 'http://localhost:5000/api/market-rankings'
            rankings_response = session.get(rankings_url)
            print(f"API响应状态: {rankings_response.status_code}")
            
            if rankings_response.status_code == 200:
                try:
                    data = rankings_response.json()
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
                except Exception as e:
                    print(f"解析JSON失败: {e}")
                    print(f"响应内容: {rankings_response.text}")
            
            # 测试全市场数据API
            print("\n=== 测试全市场数据API ===")
            market_all_url = 'http://localhost:5000/api/market-all'
            market_all_response = session.get(market_all_url)
            print(f"API响应状态: {market_all_response.status_code}")
            
            if market_all_response.status_code == 200:
                try:
                    data = market_all_response.json()
                    print(f"状态: {data.get('status')}")
                    print(f"数据源: {data.get('data_source')}")
                    if data.get('data'):
                        print(f"数据数量: {len(data['data'])}")
                        print("\n全市场数据示例:")
                        for i, stock in enumerate(data['data'][:3]):
                            print(f"{i+1}. {stock['name']} ({stock['code']}): {stock['price']} - {stock['change_pct']:.2f}%")
                except Exception as e:
                    print(f"解析JSON失败: {e}")
                    print(f"响应内容: {market_all_response.text}")
        else:
            print("❌ 登录失败")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    print("开始测试前端API...")
    test_api_endpoints()
    print("\n测试完成!")
