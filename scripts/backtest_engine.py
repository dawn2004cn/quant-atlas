#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测引擎
"""

from typing import Dict, List, Protocol
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from utils import calculate_trading_metrics, execute_trading_strategy
from interfaces.data_fetcher_interface import DataFetcherInterface

# 导入 ta 库
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator


# 导入交易策略基类
from trading_strategies import BaseTradingStrategy


class Strategy(Protocol):
    """策略接口"""
    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        """运行策略，生成交易信号"""
        ...


class TradingStrategyAdapter:
    """交易策略适配器，用于适配 BaseTradingStrategy 到 Strategy 接口"""
    def __init__(self, trading_strategy: BaseTradingStrategy):
        self.trading_strategy = trading_strategy
    
    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        """运行策略，生成交易信号"""
        # 确保列名与 BaseTradingStrategy 期望的一致
        df = data.copy()
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        
        # 运行策略
        result = self.trading_strategy.generate_signals(df)
        
        # 将结果转换回原来的格式
        result.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Signal': 'signal'
        }, inplace=True)
        
        return result
    
    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        # 根据策略类型返回合适的开始索引
        strategy_name = self.trading_strategy.__class__.__name__
        return self.trading_strategy.get_start_idx()


class StrategyEvaluator:
    """策略评估器"""
    @staticmethod
    def evaluate(strategy: Strategy, data: pd.DataFrame, initial_capital: float) -> Dict:
        """
        评估策略性能
        
        Args:
            strategy: 策略实例
            data: 股票历史数据
            initial_capital: 初始资金
            
        Returns:
            Dict: 回测结果
        """
        if data.empty:
            return {
                'final_value': initial_capital,
                'total_return': 0,
                'annual_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'trades': [],
            }
        
        # 运行策略生成交易信号
        data_with_signals = strategy.run(data)
        
        # 确定开始索引（基于策略类型）
        start_idx = 0
        if hasattr(strategy, 'get_start_idx'):
            start_idx = strategy.get_start_idx()
        
        # 执行交易策略
        trading_result = execute_trading_strategy(data_with_signals, 'signal', initial_capital, start_idx=start_idx)
        
        # 计算交易指标
        start_date = data.iloc[0]['date']
        end_date = data.iloc[-1]['date']
        metrics = calculate_trading_metrics(
            initial_capital,
            trading_result['final_value'],
            trading_result['portfolio_values'],
            start_date,
            end_date
        )
        
        return {
            'final_value': trading_result['final_value'],
            'total_return': metrics['total_return'],
            'annual_return': metrics['annual_return'],
            'max_drawdown': metrics['max_drawdown'],
            'sharpe_ratio': metrics['sharpe_ratio'],
            'trades': trading_result['trades'],
        }


# 导入交易策略
from trading_strategies import (
    MAStrategy,
    RSIStrategy,
    TAUStrategy,
    DualMovingAverageStrategy,
    BollingerRSIReversionStrategy,
    EMAMACDContinuationStrategy,
    VolumeBreakoutStrategy,
    StochasticSwingStrategy,
    TDXPrecisionStrategy
)

# 导入测试策略
from tests.test_hold_to_end_strategy import HoldToEndStrategy

class StrategyFactory:
    """策略工厂"""
    @staticmethod
    def create_strategy(strategy_name: str) -> Strategy:
        """
        创建策略实例
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            Strategy: 策略实例
        """
        strategies = {
            # 原有策略
            'MA': TradingStrategyAdapter(MAStrategy()),
            'RSI': TradingStrategyAdapter(RSIStrategy()),
            'TAU': TradingStrategyAdapter(TAUStrategy()),
            # 新策略
            'DualMA': TradingStrategyAdapter(DualMovingAverageStrategy()),
            'BollingerRSI': TradingStrategyAdapter(BollingerRSIReversionStrategy()),
            'EMAMACD': TradingStrategyAdapter(EMAMACDContinuationStrategy()),
            'VolumeBreakout': TradingStrategyAdapter(VolumeBreakoutStrategy()),
            'Stochastic': TradingStrategyAdapter(StochasticSwingStrategy()),
            # TDX精确策略
            'TDX': TradingStrategyAdapter(TDXPrecisionStrategy()),
            # 测试策略
            'HoldToEnd': TradingStrategyAdapter(HoldToEndStrategy())
        }
        return strategies.get(strategy_name, TradingStrategyAdapter(MAStrategy()))  # 默认返回MA策略


class DataFetcher(DataFetcherInterface):
    """数据获取器"""
    def __init__(self):
        from stock_async_fetcher import StockAsyncFetcher
        from smart_data_source import SmartDataSource
        self.ds = SmartDataSource()
        self.fetcher = StockAsyncFetcher()
    
    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            pd.DataFrame: 股票历史数据
        """
        import pandas as pd
        from datetime import datetime, timedelta
        
        try:
            # 计算日期范围的天数
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            days_needed = (end_dt - start_dt).days + 1
            
            # 1. 首先尝试从本地缓存获取历史数据
            from stock_cache_db import StockCache
            
            try:
                # 从数据库缓存获取历史数据
                cache = StockCache()
                
                # 计算日期范围
                end_date_str = end_date
                start_date_str = start_date
                
                # 从缓存获取历史数据
                history_data = cache.get_stock_history(symbol, start_date_str, end_date_str)
                cache.close()
                
                if history_data and len(history_data) > 0:
                    print(f"从数据库缓存获取到 {len(history_data)} 天历史数据")
                    # 转换为 DataFrame
                    df = pd.DataFrame(history_data)
                    # 转换日期格式
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    # 过滤掉无效日期
                    df = df.dropna(subset=['date'])
                    # 安全过滤日期范围
                    mask = (df['date'] >= start_dt) & (df['date'] <= end_dt)
                    filtered_data = df[mask]
                    # 确保数据按日期排序
                    filtered_data = filtered_data.sort_values('date')
                    
                    # 检查是否有数据
                    if not filtered_data.empty:
                        return filtered_data
                    else:
                        print("数据库缓存数据范围不匹配，尝试从线上获取")
                else:
                    print("数据库缓存数据不足，尝试从线上获取")
            except Exception as cache_error:
                print(f"从缓存获取数据失败: {cache_error}")
            
            # 2. 如果缓存数据不足，从线上获取数据
            data = self.ds.get_history_data(symbol, days=max(days_needed, 365*3))
            
            if data is not None and not data.empty:
                # 转换日期格式
                data['date'] = pd.to_datetime(data['date'], errors='coerce')
                
                # 过滤掉无效日期
                data = data.dropna(subset=['date'])
                
                # 安全过滤日期范围
                mask = (data['date'] >= start_dt) & (data['date'] <= end_dt)
                filtered_data = data[mask]
                
                # 确保数据按日期排序
                filtered_data = filtered_data.sort_values('date')
                
                # 如果过滤后的数据为空，说明指定的日期范围不在获取的数据范围内
                # 这种情况通常发生在指定了未来的日期范围
                if filtered_data.empty:
                    print(f"指定的日期范围 {start_date} 到 {end_date} 不在数据范围内")
                    if not data.empty:
                        print(f"   可用数据范围: {data['date'].min().strftime('%Y-%m-%d')} 到 {data['date'].max().strftime('%Y-%m-%d')}")
                    # 不生成模拟数据，直接返回空数据
                    return pd.DataFrame()
                
                # 3. 将线上获取的数据保存到缓存
                try:
                    cache = StockCache()
                    # 转换为缓存格式
                    cache_data = []
                    for _, row in filtered_data.iterrows():
                        cache_data.append({
                            'date': row['date'].strftime('%Y-%m-%d'),
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': float(row['volume']),
                            'amount': float(row['amount'])
                        })
                    # 保存到缓存
                    cache.save_stock_history(symbol, cache_data)
                    cache.close()
                    print(f"线上数据已保存到缓存")
                except Exception as save_error:
                    print(f"保存数据到缓存失败: {save_error}")
                
                return filtered_data
            else:
                # 如果获取数据失败，直接返回空数据
                print("获取数据失败，返回空数据")
                return pd.DataFrame()
        except Exception as e:
            print(f"获取股票数据失败: {e}")
            # 发生异常时，直接返回空数据
            return pd.DataFrame()
        
        return pd.DataFrame()
    
    def fetch_fund_flow(self, code: str):
        """获取资金流数据"""
        return self.fetcher.fetch_fund_flow(code)
    
    def fetch_and_cache(self, codes):
        """获取并缓存股票数据"""
        return self.fetcher.fetch_and_cache(codes)
    
    def close(self):
        """关闭资源"""
        return self.fetcher.close()


class BacktestEngine:
    """回测引擎"""

    def __init__(self, data_fetcher: DataFetcherInterface = None, strategy_factory = None):
        self.data_fetcher = data_fetcher or DataFetcher()
        self.strategy_factory = strategy_factory or StrategyFactory()
    
    def run(self, symbol: str, strategy_name: str, start_date: str, end_date: str, initial_capital: float) -> Dict:
        """
        运行回测
        
        Args:
            symbol: 股票代码
            strategy_name: 策略名称
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            initial_capital: 初始资金
            
        Returns:
            Dict: 包含回测结果的字典
        """
        print(f"运行策略 {strategy_name} 在 {symbol} 从 {start_date} 到 {end_date}...")
        
        # 获取股票数据
        data = self.data_fetcher.get_stock_data(symbol, start_date, end_date)
        
        if data.empty:
            print("没有获取到股票数据，返回空结果")
            return {
                'final_value': initial_capital,
                'total_return': 0,
                'annual_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'trades': [],
            }
        
        # 创建策略实例
        strategy = self.strategy_factory.create_strategy(strategy_name)
        
        # 评估策略
        evaluator = StrategyEvaluator()
        result = evaluator.evaluate(strategy, data, initial_capital)
        
        # 添加股票历史数据到回测结果
        result['stock_data'] = {
            'dates': data['date'].dt.strftime('%Y-%m-%d').tolist(),
            'opens': data['open'].tolist(),
            'highs': data['high'].tolist(),
            'lows': data['low'].tolist(),
            'closes': data['close'].tolist(),
            'volumes': data['volume'].tolist()
        }
        
        print(f"回测完成: 总收益 {result['total_return']:.2f}%, 年化收益 {result['annual_return']:.2f}%")
        return result

    def backtest(self, symbol: str, strategy_name: str, start_date: str, end_date: str, initial_capital: float) -> Dict:
        """
        回测接口，兼容web_app.py中的调用
        
        Args:
            symbol: 股票代码
            strategy_name: 策略名称
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            initial_capital: 初始资金
            
        Returns:
            Dict: 包含回测结果的字典
        """
        # 转换日期格式为 YYYY-MM-DD
        start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
        
        # 调用run方法
        return self.run(
            symbol=symbol,
            strategy_name=strategy_name,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            initial_capital=initial_capital
        )

if __name__ == '__main__':
    engine = BacktestEngine()
    
    # 测试回测
    result1 = engine.run(
        symbol='600036',
        strategy_name='MA',
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_capital=100000
    )
    
    print("第一次回测结果:")
    print(f"最终价值: {result1['final_value']:.2f}")
    print(f"总收益: {result1['total_return']:.2f}%")
    print(f"年化收益: {result1['annual_return']:.2f}%")
    print(f"最大回撤: {result1['max_drawdown']:.2f}%")
    print(f"夏普比率: {result1['sharpe_ratio']:.2f}")
    print(f"交易次数: {len(result1['trades'])}")
    
    # 再次运行相同参数的回测
    result2 = engine.run(
        symbol='600036',
        strategy_name='MA',
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_capital=100000
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
