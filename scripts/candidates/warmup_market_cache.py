#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预热全市场股票列表缓存
"""
import json
import pandas as pd
from cache_factory import SmartCacheFactory


def warmup_market_cache():
    """预热全市场股票列表缓存"""
    print("预热全市场股票列表缓存...")
    
    # 初始化缓存
    cache = SmartCacheFactory.get_cache(data_type='market')
    
    # 创建模拟的全市场股票数据
    print("创建模拟的全市场股票数据...")
    
    # 模拟股票数据
    stocks = []
    stock_codes = [
        ('600519', '贵州茅台'),
        ('601318', '中国平安'),
        ('000858', '五粮液'),
        ('600036', '招商银行'),
        ('601166', '兴业银行'),
        ('600031', '三一重工'),
        ('601888', '中国中免'),
        ('600276', '恒瑞医药'),
        ('601899', '紫金矿业'),
        ('601988', '中国银行'),
        ('000001', '平安银行'),
        ('000333', '美的集团'),
        ('002594', '比亚迪'),
        ('002415', '海康威视'),
        ('000725', '京东方A'),
        ('601668', '中国建筑'),
        ('600028', '中国石化'),
        ('601288', '农业银行'),
        ('601398', '工商银行'),
        ('601628', '中国人寿')
    ]
    
    for code, name in stock_codes:
        # 生成随机价格和涨跌幅
        import random
        price = round(random.uniform(5, 2000), 2)
        change_pct = round(random.uniform(-5, 5), 2)
        change_amount = round(price * change_pct / 100, 2)
        amount = round(random.uniform(100000000, 10000000000), 2)
        volume = round(random.uniform(1000000, 100000000), 2)
        volume_ratio = round(random.uniform(0.5, 5), 2)
        turnover = round(random.uniform(0.1, 10), 2)
        prev_close = round(price - change_amount, 2)
        amplitude = round(random.uniform(0.5, 10), 2)
        pe = round(random.uniform(5, 100), 2)
        pb = round(random.uniform(0.5, 10), 2)
        total_market_cap = round(random.uniform(10000000000, 500000000000), 2)
        circulating_market_cap = round(total_market_cap * random.uniform(0.5, 1), 2)
        
        stock = {
            'code': code,
            'name': name,
            'price': price,
            'change_pct': change_pct,
            'change_amount': change_amount,
            'amount': amount,
            'volume': volume,
            'volume_ratio': volume_ratio,
            'turnover': turnover,
            'prev_close': prev_close,
            'industry': '金融' if code.startswith('60') else '科技',
            'amplitude': amplitude,
            'pe': pe,
            'pb': pb,
            'total_market_cap': total_market_cap,
            'circulating_market_cap': circulating_market_cap,
            'limit_up_reason': '',
            'first_limit_up_time': '',
            'final_limit_up_time': ''
        }
        stocks.append(stock)
    
    # 保存到缓存
    print(f"保存 {len(stocks)} 只股票到缓存...")
    cache.save_market_all_cache(stocks)
    print("缓存保存成功！")
    
    # 验证缓存
    print("验证缓存...")
    cached_stocks = cache.get_market_all_cache(max_age_minutes=10080)
    if cached_stocks:
        print(f"缓存验证成功，获取到 {len(cached_stocks)} 只股票")
        print(f"前5只股票: {[stock['code'] + ' ' + stock['name'] for stock in cached_stocks[:5]]}")
        return True
    else:
        print("缓存验证失败，无法获取缓存数据")
        return False


def main():
    """主函数"""
    print("开始预热全市场股票列表缓存...\n")
    
    success = warmup_market_cache()
    
    if success:
        print("\n预热成功！全市场股票列表缓存已准备就绪。")
    else:
        print("\n预热失败！全市场股票列表缓存无法创建。")


if __name__ == "__main__":
    main()
