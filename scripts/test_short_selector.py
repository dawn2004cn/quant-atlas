#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试短线选股功能"""

from short_term_selector import ShortTermSelector

selector = ShortTermSelector()

# 测试加载股票列表
print('=== 测试加载股票列表 ===')
watchlist = selector.load_watchlist(market='all')
print(f'加载到 {len(watchlist)} 只股票')
if watchlist:
    print(f'前10只: {watchlist[:10]}')

# 测试分析单只股票
if watchlist:
    print('\n=== 测试分析单只股票 ===')
    test_code = watchlist[0]
    result = selector.analyze_single_stock(test_code)
    if result:
        print(f"股票: {result['name']}({result['code']})")
        print(f"评分: {result['score']}")
        print(f"评级: {result['rating']}")
        print(f"推荐: {result['recommend']}")
        print(f"买入信号: {result['buy_signals']}")
    else:
        print('分析失败')

# 测试选股
print('\n=== 测试选股 ===')
top_stocks = selector.select_top_stocks(top_n=3, market='all')
print(f'选出 {len(top_stocks)} 只股票')
for stock in top_stocks:
    print(f"  - {stock['name']}({stock['code']}): {stock['score']}分, 评级: {stock['rating']}, 推荐: {stock['recommend']}")

selector.close()
