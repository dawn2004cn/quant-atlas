#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试TDX策略的回测结果
"""

from backtest_engine import BacktestEngine


def test_tdx_strategy():
    """测试TDX策略"""
    print("=" * 60)
    print("测试TDX策略")
    print("=" * 60)
    
    # 初始化回测引擎
    engine = BacktestEngine()
    
    # 测试股票：601318 中国平安
    symbol = '601318'
    strategy_name = 'TDX'
    start_date = '2025-04-06'
    end_date = '2026-04-06'
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
    
    # 检查交易记录
    print("\n交易记录:")
    if result['trades']:
        for i, trade in enumerate(result['trades']):
            print(f"交易 {i+1}: {trade['date']} {trade['action']} @ {trade['price']:.2f} 数量: {trade['qty']:.0f}")
            if trade['action'] == 'SELL':
                print(f"  盈亏: {trade['profit']:.2f}")
        
        # 检查最后一次交易是否是买入
        last_trade = result['trades'][-1]
        if last_trade['action'] == 'BUY':
            print("\n最后一次交易是买入，说明当前持有股票")
            # 获取最后一天的收盘价
            last_close = result['stock_data']['closes'][-1]
            print(f"最后一天的收盘价: {last_close:.2f}")
            print(f"最后一次买入价格: {last_trade['price']:.2f}")
            print(f"持有数量: {last_trade['qty']:.0f}")
            
            # 计算预期的最终价值
            expected_value = last_trade['qty'] * last_close
            print(f"预期最终价值: {expected_value:.2f}")
            print(f"实际最终价值: {result['final_value']:.2f}")
            print(f"差值: {abs(result['final_value'] - expected_value):.2f}")
        else:
            print("\n最后一次交易是卖出，说明当前没有持有股票")
            print("最终价值应该等于当前资金")
    else:
        print("无交易记录")
    
    # 检查股票数据的最后一天
    print("\n股票数据的最后一天:")
    if 'stock_data' in result:
        last_date = result['stock_data']['dates'][-1]
        last_close = result['stock_data']['closes'][-1]
        print(f"最后一天: {last_date}, 收盘价: {last_close:.2f}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_tdx_strategy()
