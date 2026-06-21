#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数
"""

from typing import Dict, List, Optional
import numpy as np
from datetime import datetime, timedelta


def calculate_trading_metrics(initial_capital: float, final_value: float, 
                            portfolio_values: list, start_date: datetime, 
                            end_date: datetime) -> Dict:
    """
    计算交易指标
    
    Args:
        initial_capital: 初始资金
        final_value: 最终价值
        portfolio_values: 投资组合价值序列
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        Dict: 交易指标
    """
    # 计算总收益率
    total_return = (final_value - initial_capital) / initial_capital * 100
    
    # 计算年化收益率
    total_days = (end_date - start_date).days
    if total_days > 0:
        annual_return = (pow((final_value / initial_capital), (365 / total_days)) - 1) * 100
    else:
        annual_return = 0
    
    # 计算最大回撤
    max_drawdown = 0
    if portfolio_values:
        portfolio_values = np.array(portfolio_values)
        peak = portfolio_values[0]
        
        for value in portfolio_values[1:]:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    # 计算夏普比率 (简化计算)
    sharpe_ratio = 0
    if len(portfolio_values) > 1:
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252)
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio
    }


def execute_trading_strategy(data, signal_column, initial_capital, start_idx=1) -> Dict:
    """
    执行交易策略
    
    Args:
        data: 股票历史数据
        signal_column: 信号列名
        initial_capital: 初始资金
        start_idx: 开始索引
        
    Returns:
        Dict: 交易结果
    """
    capital = initial_capital
    shares = 0
    buy_price = 0  # 保存买入价格
    trades = []
    portfolio_values = []
    
    for i in range(start_idx, len(data)):
        date = data.iloc[i]['date']
        price = data.iloc[i]['close']
        signal = data.iloc[i][signal_column]
        prev_signal = data.iloc[i-1][signal_column]
        
        # 交易逻辑
        if signal == 1 and prev_signal != 1:
            # 买入
            if capital > 0:
                shares = capital / price
                buy_price = price  # 保存买入价格
                capital = 0
                # 处理日期，确保它是字符串格式
                if isinstance(date, str):
                    trade_date = date
                else:
                    trade_date = date.strftime('%Y-%m-%d')
                trades.append({
                    'date': trade_date,
                    'action': 'BUY',
                    'price': price,
                    'qty': shares,
                    'amount': shares * price,
                    'profit': 0
                })
        elif signal == -1 and prev_signal != -1:
            # 卖出
            if shares > 0:
                capital = shares * price
                profit = capital - (shares * buy_price)  # 使用买入价格计算盈亏
                # 处理日期，确保它是字符串格式
                if isinstance(date, str):
                    trade_date = date
                else:
                    trade_date = date.strftime('%Y-%m-%d')
                trades.append({
                    'date': trade_date,
                    'action': 'SELL',
                    'price': price,
                    'qty': shares,
                    'amount': capital,
                    'profit': profit
                })
                shares = 0
                buy_price = 0  # 重置买入价格
        
        # 计算当前 portfolio 价值
        current_value = capital + (shares * price)
        portfolio_values.append(current_value)
    
    # 计算最终价值
    if shares > 0:
        final_value = capital + (shares * data.iloc[-1]['close'])
    else:
        final_value = capital
    
    return {
        'final_value': final_value,
        'trades': trades,
        'portfolio_values': portfolio_values
    }
