#!/usr/bin/env python3
"""测试API回测接口"""
import requests
import json

# API地址
api_url = 'http://localhost:5000/api/backtest'

# 测试数据
test_data = {
    'symbol': '600036',
    'strategy': 'MA',
    'start_date': '2024-01-01',
    'end_date': '2024-12-31',
    'initial_capital': 100000
}

print("测试API回测接口")
print(f"股票: {test_data['symbol']}")
print(f"策略: {test_data['strategy']}")
print(f"日期: {test_data['start_date']} 到 {test_data['end_date']}")
print("=" * 60)

# 发送POST请求
try:
    response = requests.post(
        api_url,
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    print(f"响应状态码: {response.status_code}")
    
    # 解析响应
    result = response.json()
    print(f"响应状态: {result.get('status')}")
    
    if result.get('status') == 'success':
        data = result.get('data')
        print(f"最终价值: {data.get('final_value')}")
        print(f"总收益: {data.get('total_return')}%")
        print(f"年化收益: {data.get('annual_return')}%")
        print(f"交易次数: {len(data.get('trades', []))}")
        
        if data.get('trades'):
            print("\n交易记录:")
            for trade in data['trades'][:3]:
                print(f"  {trade['date']}: {trade['action']} @ {trade['price']}")
        else:
            print("\n无交易记录")
    else:
        print(f"错误信息: {result.get('message')}")
        
except Exception as e:
    print(f"测试失败: {e}")

print("\n测试完成！")
