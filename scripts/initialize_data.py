#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化数据脚本
"""

from redis_cache import RedisCache

def initialize_data():
    """初始化数据"""
    print("开始初始化数据...")
    
    cache = RedisCache()
    
    try:
        # 初始化监控数据
        print("1. 初始化监控数据...")
        # 监控数据会在获取全市场数据时自动更新
        print("✅ 监控数据初始化完成")
        
        # 初始化自选股分组
        print("2. 初始化自选股分组...")
        # 使用默认分组ID方法
        group_id = cache.get_default_group_id()
        print(f"✅ 自选股分组ID: {group_id}")
        
        # 添加默认股票到自选股
        print("3. 添加默认股票到自选股...")
        default_stocks = ['600519', '601318', '600036']
        for code in default_stocks:
            success = cache.add_stock_to_group(code, group_id)
            if success:
                print(f"✅ 添加股票 {code} 到自选股")
            else:
                print(f"⚠️ 股票 {code} 可能已在自选股中")
        
        # 初始化全市场数据
        print("4. 初始化全市场数据...")
        from stock_async_fetcher import fetch_all_market
        fetch_all_market()
        print("✅ 全市场数据初始化完成")
        
        print("\n🎉 数据初始化完成！")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
    finally:
        # 关闭连接
        cache.close()

if __name__ == '__main__':
    initialize_data()
