#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线技术指标计算
"""
import pandas as pd
from typing import Tuple, Dict

# 导入 ta 库
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
from ta.volatility import BollingerBands, AverageTrueRange


class ShortTermIndicators:
    """短线技术指标"""

    def calc_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI"""
        return RSIIndicator(close=df['close'], window=period).rsi()

    def calc_kdj(self, df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算KDJ"""
        stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=n, smooth_window=m1)
        # ta: stoch=原始 %K，stoch_signal=平滑 %D；通达信 K/D 与之对调
        stoch_k = stoch.stoch()
        stoch_d = stoch.stoch_signal()
        k = stoch_d
        d = stoch_k
        j = 3 * k - 2 * d
        return k, d, j

    def detect_kdj_cross(self, k: pd.Series, d: pd.Series, j: pd.Series) -> Dict:
        """检测KDJ交叉"""
        return {
            'golden_cross': k.iloc[-1] > d.iloc[-1] and k.iloc[-2] < d.iloc[-2],
            'death_cross': k.iloc[-1] < d.iloc[-1] and k.iloc[-2] > d.iloc[-2],
            'oversold': j.iloc[-1] < 0,
            'overbought': j.iloc[-1] > 100,
            'score': 10 if k.iloc[-1] > d.iloc[-1] else 0,
            'signal': 'golden_cross' if k.iloc[-1] > d.iloc[-1] and k.iloc[-2] < d.iloc[-2] else '',
            'k': k.iloc[-1],
            'd': d.iloc[-1],
            'j': j.iloc[-1]
        }

    def calc_macd_short(self, df: pd.DataFrame, short: int = 12, long: int = 26, mid: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD"""
        macd_indicator = MACD(close=df['close'], window_slow=long, window_fast=short, window_sign=mid)
        dif = macd_indicator.macd()
        dea = macd_indicator.macd_signal()
        macd_hist = macd_indicator.macd_diff() * 2  # 保持与原实现一致
        return dif, dea, macd_hist

    def detect_macd_cross(self, dif: pd.Series, dea: pd.Series, macd_hist: pd.Series) -> Dict:
        """检测MACD交叉"""
        return {
            'golden_cross': dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] < dea.iloc[-2],
            'death_cross': dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] > dea.iloc[-2],
            'signal': 'MACD翻红' if macd_hist.iloc[-1] > 0 and macd_hist.iloc[-2] < 0 else '',
            'dif': dif.iloc[-1],
            'dea': dea.iloc[-1],
            'macd_hist': macd_hist.iloc[-1]
        }

    def calc_bollinger(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带"""
        bollinger = BollingerBands(close=df['close'], window=period, window_dev=std_dev)
        upper = bollinger.bollinger_hband()
        middle = bollinger.bollinger_mavg()
        lower = bollinger.bollinger_lband()
        return upper, middle, lower

    def detect_bollinger_signal(self, df: pd.DataFrame, upper: pd.Series, middle: pd.Series, lower: pd.Series) -> Dict:
        """检测布林带信号"""
        return {
            'signal': '下轨反弹' if df['close'].iloc[-1] > lower.iloc[-1] and df['close'].iloc[-2] < lower.iloc[-2] else '',
            'position_pct': (df['close'].iloc[-1] - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]) * 100 if upper.iloc[-1] != lower.iloc[-1] else 50,
            'upper': upper.iloc[-1],
            'middle': middle.iloc[-1],
            'lower': lower.iloc[-1],
            'bandwidth': (upper.iloc[-1] - lower.iloc[-1]) / middle.iloc[-1] * 100 if middle.iloc[-1] != 0 else 0
        }

    def detect_volume_surge(self, df: pd.DataFrame, ratio: float = 1.5) -> Dict:
        """检测成交量异动"""
        return {
            'surge_type': '放量上涨' if df['volume'].iloc[-1] > df['volume'].iloc[-2] * ratio and df['close'].iloc[-1] > df['close'].iloc[-2] else '',
            'volume_ratio': df['volume'].iloc[-1] / df['volume'].iloc[-2] if df['volume'].iloc[-2] != 0 else 1,
            'price_change': (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100 if df['close'].iloc[-2] != 0 else 0
        }

    def calc_atr_short(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算ATR"""
        return AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=period).average_true_range()

    def calc_trade_points(self, current_price: float, atr: float, stop_multiplier: float, profit_multiplier: float) -> Dict:
        """计算交易点位"""
        return {
            'buy_price': current_price,
            'stop_loss': current_price - atr * stop_multiplier,
            'take_profit': current_price + atr * profit_multiplier,
            'stop_loss_pct': (atr * stop_multiplier) / current_price * 100,
            'take_profit_pct': (atr * profit_multiplier) / current_price * 100,
            'atr': atr,
            'atr_pct': atr / current_price * 100,
            'risk_reward_ratio': profit_multiplier / stop_multiplier
        }
