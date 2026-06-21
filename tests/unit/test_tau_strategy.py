#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试TAU策略
"""

from backtest_engine import BacktestEngine, TAUStrategy
import pandas as pd


def test_tau_strategy():
    """测试TAU策略"""
    print("=" * 60)
    print("测试TAU策略")
    print("=" * 60)
    
    # 初始化回测引擎
    engine = BacktestEngine()
    
    # 测试股票：601318 中国平安
    symbol = '601318'
    strategy_name = 'TAU'
    start_date = '2025-04-01'
    end_date = '2026-04-01'
    initial_capital = 100000
    
    # 运行回测
    print(f"\n运行TAU策略在 {symbol} 从 {start_date} 到 {end_date}...")
    result = engine.run(
        symbol=symbol,
        strategy_name=strategy_name,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    print("\n回测结果:")
    print(f"最终价值: {result['final_value']:.2f}")
    print(f"总收益: {result['total_return']:.2f}%")
    print(f"年化收益: {result['annual_return']:.2f}%")
    print(f"最大回撤: {result['max_drawdown']:.2f}%")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"交易次数: {len(result['trades'])}")
    
    # 查看交易详情
    if result['trades']:
        print("\n交易详情:")
        for i, trade in enumerate(result['trades']):
            if trade['action'] == 'SELL':
                print(f"交易 {i+1}: {trade['action']} at {trade['price']:.2f} on {trade['date']}, 盈亏: {trade['profit']:.2f}")
            else:
                print(f"交易 {i+1}: {trade['action']} at {trade['price']:.2f} on {trade['date']}")
    else:
        print("\n没有交易记录")
    
    # 测试策略的信号生成
    print("\n测试TAU策略信号生成:")
    # 获取股票数据
    data = engine.data_fetcher.get_stock_data(symbol, start_date, end_date)
    
    if not data.empty:
        # 创建TAU策略实例
        tau_strategy = TAUStrategy()
        # 运行策略生成信号
        data_with_signals = tau_strategy.run(data)
        
        # 查看信号分布
        print(f"\n信号分布:")
        print(data_with_signals['signal'].value_counts())
        
        # 查看评分分布
        print(f"\n评分分布:")
        print(f"平均评分: {data_with_signals['Total_Score'].mean():.2f}")
        print(f"评分最小值: {data_with_signals['Total_Score'].min():.2f}")
        print(f"评分最大值: {data_with_signals['Total_Score'].max():.2f}")
        
        # 查看前20行数据
        print("\n前20行数据:")
        print(data_with_signals[['date', 'close', 'Trend_Score', 'Activity_Score', 'Total_Score', 'signal']].head(20))
        
        # 查看最后20行数据
        print("\n最后20行数据:")
        print(data_with_signals[['date', 'close', 'Trend_Score', 'Activity_Score', 'Total_Score', 'signal']].tail(20))
    else:
        print("没有获取到股票数据")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_tau_strategy()
