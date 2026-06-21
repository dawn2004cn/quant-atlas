#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试回测引擎是否正确返回股票历史数据
"""

from backtest_engine import BacktestEngine


def test_backtest_chart_data():
    """测试回测引擎是否正确返回股票历史数据"""
    print("=" * 60)
    print("测试回测引擎是否正确返回股票历史数据")
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
        print(f"开盘价范围: {min(stock_data['opens']):.2f} 到 {max(stock_data['opens']):.2f}")
        print(f"收盘价范围: {min(stock_data['closes']):.2f} 到 {max(stock_data['closes']):.2f}")
        print("股票历史数据包含以下字段:")
        for key in stock_data:
            print(f"  - {key}: {len(stock_data[key])} 条数据")
    else:
        print("❌ 回测结果中没有股票历史数据")
    
    # 检查交易记录
    print("\n交易记录:")
    if result['trades']:
        for i, trade in enumerate(result['trades']):
            print(f"交易 {i+1}: {trade['date']} {trade['action']} @ {trade['price']:.2f}")
    else:
        print("无交易记录")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_backtest_chart_data()
