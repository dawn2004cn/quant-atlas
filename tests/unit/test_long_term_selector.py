#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试中长线选股功能
"""

from long_term_selector import LongTermSelector


def test_long_term_selector():
    """测试中长线选股功能"""
    print("=" * 60)
    print("测试中长线选股功能")
    print("=" * 60)
    
    # 初始化选股器
    selector = LongTermSelector()
    
    # 测试加载股票列表
    print("\n1. 测试加载股票列表:")
    watchlist = selector.load_watchlist(market='all')
    print(f"加载到 {len(watchlist)} 只股票")
    print(f"前10只股票: {watchlist[:10]}")
    
    # 测试分析单只股票
    print("\n2. 测试分析单只股票:")
    test_stock = '601318'  # 中国平安
    stock_result = selector.analyze_single_stock(test_stock)
    if stock_result:
        print(f"股票: {stock_result['name']} ({stock_result['code']})")
        print(f"评分: {stock_result['score']}")
        print(f"评级: {stock_result['rating']}")
        print(f"推荐: {stock_result['recommend']}")
        print(f"触发策略: {stock_result['buy_signals']}")
    else:
        print(f"分析股票 {test_stock} 失败")
    
    # 测试选股
    print("\n3. 测试选股:")
    top_stocks = selector.select_top_stocks(top_n=5, market='all')
    print(f"选出 {len(top_stocks)} 只股票")
    
    if top_stocks:
        print("\n选股结果:")
        for i, stock in enumerate(top_stocks):
            print(f"{i+1}. {stock['name']} ({stock['code']}): {stock['score']}分, 评级: {stock['rating']}, 推荐: {stock['recommend']}")
    else:
        print("没有选出股票")
    
    # 关闭资源
    selector.close()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_long_term_selector()
