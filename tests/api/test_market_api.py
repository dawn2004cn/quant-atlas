#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试市场情绪和市场异动API
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_market_sentiment():
    """测试市场情绪API"""
    print("测试市场情绪API...")
    
    try:
        url = f"{BASE_URL}/api/market/sentiment"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"市场情绪API响应成功: {response.status_code}")
            print(f"市场情绪得分: {data['data']['score']}")
            print(f"市场情绪等级: {data['data']['level']}")
            print(f"更新时间: {data['data']['update_time']}")
            print(f"数据源: {'历史缓存' if data['data'].get('is_historical') else '实时'}")
            print(f"统计数据: {data['data']['stats']}")
            return True
        else:
            print(f"市场情绪API响应失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"测试市场情绪API失败: {e}")
        return False

def test_market_movements():
    """测试市场异动API"""
    print("\n测试市场异动API...")
    
    try:
        url = f"{BASE_URL}/api/market/movements"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"市场异动API响应成功: {response.status_code}")
            print(f"市场异动数据数量: {len(data['data'])}")
            print(f"数据源: {data['data_source']}")
            
            if data['data']:
                print("前5条市场异动数据:")
                for i, item in enumerate(data['data'][:5]):
                    print(f"  {i+1}. {item['name']} ({item['code']}): {item['type']} - {item['change']}")
            return True
        else:
            print(f"市场异动API响应失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"测试市场异动API失败: {e}")
        return False

def test_market_rankings():
    """测试市场榜单API"""
    print("\n测试市场榜单API...")
    
    try:
        url = f"{BASE_URL}/api/market-rankings"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"市场榜单API响应成功: {response.status_code}")
            print(f"涨幅榜数据数量: {len(data['data'].get('up_rank', []))}")
            print(f"跌幅榜数据数量: {len(data['data'].get('down_rank', []))}")
            print(f"成交量榜数据数量: {len(data['data'].get('volume_rank', []))}")
            print(f"成交额榜数据数量: {len(data['data'].get('amount_rank', []))}")
            return True
        else:
            print(f"市场榜单API响应失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    except Exception as e:
        print(f"测试市场榜单API失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试市场相关API...\n")
    
    success_count = 0
    total_count = 3
    
    if test_market_sentiment():
        success_count += 1
    
    if test_market_movements():
        success_count += 1
    
    if test_market_rankings():
        success_count += 1
    
    print(f"\n测试结果: {success_count}/{total_count} 个API测试通过")
    
    if success_count == total_count:
        print("所有市场相关API测试通过！")
    else:
        print("部分API测试失败，请检查日志了解详情。")

if __name__ == "__main__":
    main()
