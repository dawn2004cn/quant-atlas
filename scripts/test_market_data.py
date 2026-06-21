#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试市场数据获取
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_service import MarketService
from cache_factory import CacheFactory
import requests
import json


def test_market_rankings():
    """测试市场排行榜数据获取"""
    print("\n=== 测试市场排行榜 ===")
    market_service = MarketService()
    
    try:
        result = market_service.get_market_rankings()
        print(f"状态: {result.get('status')}")
        print(f"数据源: {result.get('data_source')}")
        
        if result.get('status') == 'success':
            data = result.get('data', {})
            print(f"涨幅榜数量: {len(data.get('gainers', []))}")
            print(f"跌幅榜数量: {len(data.get('losers', []))}")
            print(f"成交额榜数量: {len(data.get('amounts', []))}")
            print(f"换手率榜数量: {len(data.get('turnovers', []))}")
            
            # 打印涨幅榜前3名
            if data.get('gainers'):
                print("\n涨幅榜前3名:")
                for i, stock in enumerate(data['gainers'][:3]):
                    print(f"{i+1}. {stock['name']} ({stock['code']}): {stock['change_pct']:.2f}%")
        else:
            print(f"错误信息: {result.get('message')}")
            
    except Exception as e:
        print(f"测试市场排行榜失败: {e}")


def test_market_movements():
    """测试市场异动数据获取"""
    print("\n=== 测试市场异动 ===")
    
    try:
        # 测试搜狐API
        url = 'https://hqm.stock.sohu.com/gethqtop.up?cb=fortune_hq'
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        print(f"搜狐API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            # 处理响应
            response_content = response.content
            print(f"响应字节长度: {len(response_content)}")
            
            # 尝试不同的编码
            encodings = ['gbk', 'utf-8', 'gb2312']
            response_text = None
            
            for encoding in encodings:
                try:
                    response_text = response_content.decode(encoding)
                    print(f"编码 {encoding} 解码成功")
                    break
                except Exception as e:
                    print(f"编码 {encoding} 解码失败: {e}")
                    continue
            
            if response_text:
                print(f"响应长度: {len(response_text)}")
                print(f"响应开头: {response_text[:100]}...")
                print(f"响应结尾: ...{response_text[-50:]}")
                
                # 检查是否包含JSONP包装
                if 'fortune_hq(' in response_text:
                    print("找到JSONP包装")
                else:
                    print("未找到JSONP包装")
        else:
            print(f"搜狐API请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"测试市场异动失败: {e}")


def test_cache_status():
    """测试缓存状态"""
    print("\n=== 测试缓存状态 ===")
    
    try:
        cache = CacheFactory.get_cache()
        
        # 测试市场排行榜缓存
        cached_stocks = cache.get_market_all_cache(max_age_minutes=30)
        if cached_stocks:
            print(f"市场数据缓存存在，数量: {len(cached_stocks)}")
        else:
            print("市场数据缓存不存在")
        
        # 测试市场异动缓存
        cached_movements = cache.get_market_movements(limit=20)
        if cached_movements:
            print(f"市场异动缓存存在，数量: {len(cached_movements)}")
        else:
            print("市场异动缓存不存在")
            
    except Exception as e:
        print(f"测试缓存状态失败: {e}")


def test_akshare_connection():
    """测试akshare连接"""
    print("\n=== 测试akshare连接 ===")
    
    try:
        import akshare as ak
        import time
        
        start_time = time.time()
        df = ak.stock_zh_a_spot_em()
        end_time = time.time()
        
        print(f"akshare获取成功，耗时: {end_time - start_time:.2f}秒")
        print(f"数据行数: {len(df)}")
        print(f"列名: {list(df.columns)}")
        
        if not df.empty:
            print("前5行数据:")
            print(df.head())
        else:
            print("获取的数据为空")
            
    except Exception as e:
        print(f"akshare连接失败: {e}")


if __name__ == "__main__":
    print("开始测试市场数据获取...")
    
    # 测试缓存状态
    test_cache_status()
    
    # 测试akshare连接
    test_akshare_connection()
    
    # 测试市场排行榜
    test_market_rankings()
    
    # 测试市场异动
    test_market_movements()
    
    print("\n测试完成!")
