#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 API 路由返回换手率数据
"""
from web_app import app
import json

print("测试 API 路由返回换手率数据...")
print("=" * 60)

with app.test_client() as client:
    # 先登录
    print("0. 登录...")
    login_data = {
        'username': 'admin',
        'password': 'changeme'
    }
    response = client.post('/login', data=login_data, follow_redirects=True)
    
    # 测试 /api/stocks 路由
    print("1. 测试 /api/stocks 路由...")
    response = client.get('/api/stocks')
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data.decode('utf-8')}")
    
    try:
        data = json.loads(response.data)
        if data['status'] == 'success':
            print(f"✅ 成功获取 {len(data['data'])} 只股票数据")
            for stock in data['data']:
                print(f"   {stock['code']} - {stock['name']}: 换手率 {stock.get('turnover', 0):.2f}%")
        else:
            print(f"❌ 失败: {data.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 解析 JSON 失败: {e}")
    
    print("-" * 40)
    
    # 测试 /api/stocks/realtime 路由
    print("2. 测试 /api/stocks/realtime 路由...")
    response = client.get('/api/stocks/realtime')
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data.decode('utf-8')}")
    
    try:
        data = json.loads(response.data)
        if data['status'] == 'success':
            print(f"✅ 成功获取 {len(data['data'])} 只股票数据")
            for stock in data['data']:
                print(f"   {stock['code']} - {stock['name']}: 换手率 {stock.get('turnover', 0):.2f}%")
        else:
            print(f"❌ 失败: {data.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 解析 JSON 失败: {e}")

print("\n测试完成！")
