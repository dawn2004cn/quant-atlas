#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试回测引擎的缓存回退功能
"""

from backtest_engine import BacktestEngine


def test_backtest_cache():
    """测试回测引擎的缓存回退功能"""
    print("=" * 60)
    print("测试回测引擎的缓存回退功能")
    print("=" * 60)
    
    # 初始化回测引擎
    engine = BacktestEngine()
    
    # 测试股票：601318 中国平安
    symbol = '601318'
    strategy_name = 'MA'
    start_date = '2025-04-01'
    end_date = '2026-04-01'
    initial_capital = 100000
    
    # 第一次回测（应该从线上获取数据并保存到缓存）
    print("\n第一次回测（从线上获取数据）:")
    result1 = engine.run(
        symbol=symbol,
        strategy_name=strategy_name,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    print("\n第一次回测结果:")
    print(f"最终价值: {result1['final_value']:.2f}")
    print(f"总收益: {result1['total_return']:.2f}%")
    print(f"年化收益: {result1['annual_return']:.2f}%")
    print(f"最大回撤: {result1['max_drawdown']:.2f}%")
    print(f"夏普比率: {result1['sharpe_ratio']:.2f}")
    print(f"交易次数: {len(result1['trades'])}")
    
    # 第二次回测（应该从缓存获取数据）
    print("\n第二次回测（从缓存获取数据）:")
    result2 = engine.run(
        symbol=symbol,
        strategy_name=strategy_name,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    print("\n第二次回测结果:")
    print(f"最终价值: {result2['final_value']:.2f}")
    print(f"总收益: {result2['total_return']:.2f}%")
    print(f"年化收益: {result2['annual_return']:.2f}%")
    print(f"最大回撤: {result2['max_drawdown']:.2f}%")
    print(f"夏普比率: {result2['sharpe_ratio']:.2f}")
    print(f"交易次数: {len(result2['trades'])}")
    
    # 比较两次结果
    print("\n两次回测结果是否一致:")
    print(f"最终价值一致: {abs(result1['final_value'] - result2['final_value']) < 0.01}")
    print(f"总收益一致: {abs(result1['total_return'] - result2['total_return']) < 0.01}")
    print(f"年化收益一致: {abs(result1['annual_return'] - result2['annual_return']) < 0.01}")
    print(f"最大回撤一致: {abs(result1['max_drawdown'] - result2['max_drawdown']) < 0.01}")
    print(f"夏普比率一致: {abs(result1['sharpe_ratio'] - result2['sharpe_ratio']) < 0.01}")
    print(f"交易次数一致: {len(result1['trades']) == len(result2['trades'])}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_backtest_cache()
