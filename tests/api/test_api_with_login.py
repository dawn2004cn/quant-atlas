#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API端点（带登录）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests


def test_api_with_login():
    """测试API端点（带登录）"""
    print("=== 测试API端点（带登录）===")
    
    try:
        # 创建session
        session = requests.Session()
        
        # 登录
        login_url = 'http://localhost:5000/login'
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        # 先获取登录页面，获取csrf token
        session.get(login_url)
        
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
                print(f"响应内容: {movements_response.text[:500]}...")
                try:
                    data = movements_response.json()
                    print(f"状态: {data.get('status')}")
                    print(f"数据源: {data.get('data_source')}")
                    print(f"数据数量: {len(data.get('data', []))}")
                except Exception as e:
                    print(f"解析JSON失败: {e}")
            
            # 测试市场排行榜API
            print("\n=== 测试市场排行榜API ===")
            rankings_url = 'http://localhost:5000/api/market-rankings'
            rankings_response = session.get(rankings_url)
            print(f"API响应状态: {rankings_response.status_code}")
            
            if rankings_response.status_code == 200:
                print(f"响应内容: {rankings_response.text[:500]}...")
                try:
                    data = rankings_response.json()
                    print(f"状态: {data.get('status')}")
                    print(f"数据源: {data.get('data_source')}")
                    if data.get('data'):
                        rankings = data['data']
                        print(f"涨幅榜数量: {len(rankings.get('gainers', []))}")
                        print(f"跌幅榜数量: {len(rankings.get('losers', []))}")
                except Exception as e:
                    print(f"解析JSON失败: {e}")
        else:
            print("❌ 登录失败")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    print("开始测试API端点（带登录）...")
    test_api_with_login()
    print("\n测试完成!")
