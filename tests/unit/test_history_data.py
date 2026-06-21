#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试历史数据缓存功能
"""

import os
import sys
from datetime import datetime, timedelta

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from stock_cache_db import StockCache

def test_history_data():
    """测试历史数据缓存"""
    print("🚀 测试历史数据缓存功能...")
    
    cache = StockCache()
    
    try:
        # 测试1: 检查历史数据是否保存成功
        print("\n1️⃣ 测试历史数据保存")
        
        # 随机选择几只股票进行测试
        test_stocks = ['600519', '601318', '000858']
        
        for stock_code in test_stocks:
            # 获取历史数据
            history = cache.get_stock_history(stock_code)
            
            if history:
                print(f"✅ {stock_code} 历史数据: {len(history)} 条")
                print(f"   最早日期: {history[0]['date']}")
                print(f"   最晚日期: {history[-1]['date']}")
                
                # 打印最近几条数据
                print("   最近5条数据:")
                for item in history[-5:]:
                    print(f"     {item['date']}: {item['close']:.2f}")
            else:
                print(f"❌ {stock_code} 历史数据为空")
        
        # 测试2: 检查更新状态
        print("\n2️⃣ 测试更新状态")
        
        for stock_code in test_stocks:
            status = cache.get_stock_history_status(stock_code)
            if status:
                print(f"✅ {stock_code} 更新状态:")
                print(f"   最后更新日期: {status['last_updated_date']}")
                print(f"   最后检查日期: {status['last_check_date']}")
            else:
                print(f"❌ {stock_code} 无更新状态")
        
        # 测试3: 测试日期范围查询
        print("\n3️⃣ 测试日期范围查询")
        
        stock_code = test_stocks[0]
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        history = cache.get_stock_history(stock_code, start_date, end_date)
        if history:
            print(f"✅ {stock_code} 近30天数据: {len(history)} 条")
            print(f"   日期范围: {start_date} 到 {end_date}")
        else:
            print(f"❌ {stock_code} 近30天数据为空")
        
        # 测试4: 测试自动更新逻辑
        print("\n4️⃣ 测试自动更新逻辑")
        
        # 模拟一个已经更新到今天的股票
        today = datetime.now().strftime('%Y-%m-%d')
        cache.update_stock_history_status(test_stocks[0], today)
        
        # 检查更新状态
        status = cache.get_stock_history_status(test_stocks[0])
        if status and status['last_updated_date'] == today:
            print(f"✅ {test_stocks[0]} 自动更新逻辑测试成功")
        else:
            print(f"❌ {test_stocks[0]} 自动更新逻辑测试失败")
        
        print("\n✅ 历史数据缓存测试完成")
        
    finally:
        cache.close()

if __name__ == '__main__':
    test_history_data()
