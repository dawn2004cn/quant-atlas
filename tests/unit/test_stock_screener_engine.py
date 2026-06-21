#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试StockScreenerEngine选股引擎
"""

from long_term_selector import LongTermSelector


def test_stock_screener_engine():
    """测试StockScreenerEngine选股引擎"""
    print("=" * 60)
    print("测试StockScreenerEngine选股引擎")
    print("=" * 60)
    
    # 初始化选股器
    selector = LongTermSelector()
    
    # 测试分析单只股票，确保从缓存中读取数据
    test_stocks = ['601318', '600036', '600519', '000858', '000333']
    
    for stock_code in test_stocks:
        print(f"\n分析股票 {stock_code}:")
        stock_result = selector.analyze_single_stock(stock_code)
        if stock_result:
            print(f"股票: {stock_result['name']} ({stock_result['code']})")
            print(f"价格: {stock_result['price']}")
            print(f"涨跌幅: {stock_result['change_pct']:.2f}%")
            print(f"评分: {stock_result['score']}")
            print(f"评级: {stock_result['rating']}")
            print(f"推荐: {stock_result['recommend']}")
            print(f"触发模型数量: {stock_result['buy_signal_count']}")
            if stock_result['buy_signals']:
                print("触发模型:")
                for signal in stock_result['buy_signals'][:3]:  # 显示前三个模型
                    print(f"  - {signal}")
                if len(stock_result['buy_signals']) > 3:
                    print(f"  - ... 等 {len(stock_result['buy_signals'])} 个模型")
        else:
            print(f"分析股票 {stock_code} 失败")
    
    # 测试不同市场的选股
    print("\n" + "=" * 60)
    print("测试不同市场的选股")
    print("=" * 60)
    
    markets = ['all', 'hs', 'chuang', 'bj']
    for market in markets:
        print(f"\n测试 {market} 市场选股:")
        top_stocks = selector.select_top_stocks(top_n=3, market=market)
        print(f"选出 {len(top_stocks)} 只股票")
        
        if top_stocks:
            for i, stock in enumerate(top_stocks):
                print(f"{i+1}. {stock['name']} ({stock['code']}): {stock['score']}分, 推荐: {stock['recommend']}")
                print(f"   触发模型数量: {stock['buy_signal_count']}")
        else:
            print("没有选出股票")
    
    # 关闭资源
    selector.close()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_stock_screener_engine()
