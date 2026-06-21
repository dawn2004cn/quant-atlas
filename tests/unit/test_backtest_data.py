#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试回测数据的正确性
"""

from backtest_engine import BacktestEngine


def test_backtest_data():
    """测试回测数据的正确性"""
    print("=" * 60)
    print("测试回测数据的正确性")
    print("=" * 60)
    
    # 初始化回测引擎
    engine = BacktestEngine()
    
    # 测试股票：601318 中国平安
    symbol = '601318'
    strategy_name = 'MA'
    start_date = '2025-04-01'
    end_date = '2026-04-01'
    initial_capital = 100000
    
    # 运行回测
    print(f"\n运行策略 {strategy_name} 在 {symbol} 从 {start_date} 到 {end_date}...")
    result = engine.run(
        symbol=symbol,
        strategy_name=strategy_name,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    # 检查回测结果
    print("\n回测结果:")
    print(f"最终价值: {result['final_value']:.2f}")
    print(f"总收益: {result['total_return']:.2f}%")
    print(f"年化收益: {result['annual_return']:.2f}%")
    print(f"最大回撤: {result['max_drawdown']:.2f}%")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"交易次数: {len(result['trades'])}")
    
    # 检查股票历史数据
    print("\n股票历史数据:")
    if 'stock_data' in result:
        stock_data = result['stock_data']
        print(f"数据长度: {len(stock_data['dates'])}")
        print(f"日期范围: {stock_data['dates'][0]} 到 {stock_data['dates'][-1]}")
        
        # 检查数据的前5天
        print("\n前5天数据:")
        print("日期\t\t开盘\t最高\t最低\t收盘")
        print("=" * 60)
        for i in range(min(5, len(stock_data['dates']))):
            date = stock_data['dates'][i]
            open_price = stock_data['opens'][i]
            high_price = stock_data['highs'][i]
            low_price = stock_data['lows'][i]
            close_price = stock_data['closes'][i]
            
            # 验证数据的合理性
            if high_price < max(open_price, close_price):
                print(f"错误 {date}: 最高价 {high_price:.2f} 小于开盘或收盘价")
            if low_price > min(open_price, close_price):
                print(f"错误 {date}: 最低价 {low_price:.2f} 大于开盘或收盘价")
            
            # 打印数据
            print(f"{date}\t{open_price:.2f}\t{high_price:.2f}\t{low_price:.2f}\t{close_price:.2f}")
        
        # 检查数据的后5天
        print("\n后5天数据:")
        print("日期\t\t开盘\t最高\t最低\t收盘")
        print("=" * 60)
        for i in range(max(0, len(stock_data['dates']) - 5), len(stock_data['dates'])):
            date = stock_data['dates'][i]
            open_price = stock_data['opens'][i]
            high_price = stock_data['highs'][i]
            low_price = stock_data['lows'][i]
            close_price = stock_data['closes'][i]
            
            # 验证数据的合理性
            if high_price < max(open_price, close_price):
                print(f"错误 {date}: 最高价 {high_price:.2f} 小于开盘或收盘价")
            if low_price > min(open_price, close_price):
                print(f"错误 {date}: 最低价 {low_price:.2f} 大于开盘或收盘价")
            
            # 打印数据
            print(f"{date}\t{open_price:.2f}\t{high_price:.2f}\t{low_price:.2f}\t{close_price:.2f}")
    else:
        print("回测结果中没有股票历史数据")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_backtest_data()
