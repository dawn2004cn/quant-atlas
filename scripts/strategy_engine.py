#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略引擎
"""
import pandas as pd
from long_term_strategies import LongTermStrategies
from trading_strategies import TDXPrecisionStrategy

class StrategyEngine:
    def __init__(self, df: pd.DataFrame, fundamental_data: dict, stock_info: dict):
        self.df = df
        self.fundamental_data = fundamental_data
        self.stock_info = stock_info
        self.strategies = LongTermStrategies()
        self.tdx_strategy = TDXPrecisionStrategy()

    def run_all_strategies(self) -> list:
        """
        运行所有中长线策略
        """
        triggered = []
        
        pe = self.fundamental_data.get('pe', 999)
        peg = self.fundamental_data.get('peg', 99)
        roe = self.fundamental_data.get('roe', 0)

        # MA趋势
        res = self.strategies.strategy_ma_trend(self.df)
        if res['signal']:
            triggered.append({'name': 'MA趋势', 'description': res['desc'], 'holding_period': '20-60天', 'score': res.get('score', 10)})
            
        # MACD趋势
        res = self.strategies.strategy_macd_trend(self.df)
        if res['signal']:
            triggered.append({'name': 'MACD趋势', 'description': res['desc'], 'holding_period': '15-30天', 'score': res.get('score', 10)})
            
        # 价值成长
        res = self.strategies.strategy_value_growth(pe, peg, roe)
        if res['signal']:
            triggered.append({'name': '价值成长', 'description': res['desc'], 'holding_period': '60-180天', 'score': res.get('score', 10)})
        
        # 突破回踩
        res = self.strategies.strategy_breakout_retrace(self.df)
        if res['signal']:
            triggered.append({'name': '突破回踩', 'description': res['desc'], 'holding_period': '10-30天', 'score': res.get('score', 10)})
            
        # 底部反转
        res = self.strategies.strategy_bottom_reversal(self.df)
        if res['signal']:
            triggered.append({'name': '底部反转', 'description': res['desc'], 'holding_period': '15-30天', 'score': res.get('score', 10)})
            
        # 趋势加速
        res = self.strategies.strategy_trend_acceleration(self.df)
        if res['signal']:
            triggered.append({'name': '趋势加速', 'description': res['desc'], 'holding_period': '10-20天', 'score': res.get('score', 10)})
            
        # 强势股回调
        res = self.strategies.strategy_strong_pullback(self.df)
        if res['signal']:
            triggered.append({'name': '强势股回调', 'description': res['desc'], 'holding_period': '5-15天', 'score': res.get('score', 10)})
            
        # TDX精确策略
        try:
            signals = self.tdx_strategy.generate_signals(self.df)
            latest_signal = signals['signal'].iloc[-1] if len(signals) > 0 else 0
            if latest_signal == 1:
                score = self.tdx_strategy.calculate_score(self.df)
                triggered.append({'name': 'TDX精确策略', 'description': '基于通达信指标的精确交易信号', 'holding_period': '10-30天', 'score': min(20, score * 0.2)})
        except Exception as e:
            print(f"运行TDX精确策略时出错: {e}")
            
        return triggered
