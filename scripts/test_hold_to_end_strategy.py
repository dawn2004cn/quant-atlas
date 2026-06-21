#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试持有股票到回测结束的策略
"""

from trading_strategies import BaseTradingStrategy
import pandas as pd


class HoldToEndStrategy(BaseTradingStrategy):
    """持有股票到回测结束的策略"""
    
    @property
    def name(self) -> str:
        return "HoldToEnd"
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        data = data.copy()
        data['Signal'] = 0
        
        # 在倒数第二天买入
        if len(data) > 1:
            data.iloc[-2, data.columns.get_loc('Signal')] = 1
        
        return data
    
    def get_start_idx(self) -> int:
        return 1


# 测试这个策略
if __name__ == '__main__':
    from backtest_engine import BacktestEngine
    
    print("=" * 60)
    print("测试持有股票到回测结束的策略")
    print("=" * 60)
    
    # 初始化回测引擎
    engine = BacktestEngine()
    
    # 测试股票：601318 中国平安
    symbol = '601318'
    strategy_name = 'HoldToEnd'  # 使用持有到结束的策略
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
    
    # 检查交易记录
    print("\n交易记录:")
    if result['trades']:
        for i, trade in enumerate(result['trades']):
            print(f"交易 {i+1}: {trade['date']} {trade['action']} @ {trade['price']:.2f}")
        
        # 检查最后一次交易是否是买入
        last_trade = result['trades'][-1]
        if last_trade['action'] == 'BUY':
            print("\n最后一次交易是买入，说明当前持有股票")
            # 获取最后一天的收盘价
            last_close = result['stock_data']['closes'][-1]
            print(f"最后一天的收盘价: {last_close:.2f}")
            print("最终价值应该包含持有股票的价值")
            
            # 计算预期的最终价值
            shares = last_trade['qty']
            expected_value = shares * last_close
            print(f"预期最终价值: {expected_value:.2f}")
            print(f"实际最终价值: {result['final_value']:.2f}")
            print(f"差值: {abs(result['final_value'] - expected_value):.2f}")
        else:
            print("\n最后一次交易是卖出，说明当前没有持有股票")
            print("最终价值应该等于当前资金")
    else:
        print("无交易记录")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
