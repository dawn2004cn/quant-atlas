#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中长线选股策略集合
包含7大中长线策略：
1. MA趋势 - 均线多头排列
2. MACD趋势 - MACD趋势确认
3. 价值成长 - 长期价值投资
4. 突破回踩 - 突破后回踩买入
5. 底部反转 - RSI+MACD双确认
6. 趋势加速 - 均线多头+放量
7. 强势股回调 - 强势股回调低吸
"""
import pandas as pd
from advanced_long_term_indicators import AdvancedLongTermIndicators

class LongTermStrategies:
    def __init__(self):
        self.indicators = AdvancedLongTermIndicators()

    def strategy_ma_trend(self, df: pd.DataFrame) -> dict:
        """
        MA趋势策略: 均线多头排列
        """
        ma5 = self.indicators.calc_ma(df, 5)
        ma10 = self.indicators.calc_ma(df, 10)
        ma20 = self.indicators.calc_ma(df, 20)
        ma60 = self.indicators.calc_ma(df, 60)
        
        if ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]:
            return {'signal': True, 'desc': '均线多头排列', 'score': 40}
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_macd_trend(self, df: pd.DataFrame) -> dict:
        """
        MACD趋势策略: MACD零轴上方金叉
        """
        dif, dea, macd_hist = self.indicators.calc_macd(df)
        if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] < dea.iloc[-2] and dif.iloc[-1] > 0:
            return {'signal': True, 'desc': 'MACD零轴上方金叉', 'score': 30}
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_value_growth(self, pe: float, peg: float, roe: float) -> dict:
        """
        价值成长策略: 低PE, 低PEG, 高ROE
        """
        score = 0
        if pe is not None and pe < 20: score += 10
        if peg is not None and peg < 1: score += 15
        if roe is not None and roe > 15: score += 15
        
        if score > 20:
            pe_str = f'{pe:.1f}' if pe is not None else 'N/A'
            peg_str = f'{peg:.1f}' if peg is not None else 'N/A'
            roe_str = f'{roe:.1f}%' if roe is not None else 'N/A'
            return {'signal': True, 'desc': f'价值成长(PE:{pe_str}, PEG:{peg_str}, ROE:{roe_str})', 'score': score}
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_breakout_retrace(self, df: pd.DataFrame) -> dict:
        """
        突破回踩策略: 突破前期高点后回踩
        逻辑：
        1. 计算前期高点（过去40天的最高价）
        2. 检查最近是否突破前期高点
        3. 突破后回踩到突破点附近（不跌破前期高点）
        4. 成交量配合突破时放大
        """
        if len(df) < 60:
            return {'signal': False, 'desc': '', 'score': 0}
        
        # 计算前期高点（过去40天的最高价，不包括最近5天）
        lookback_period = 40
        recent_period = 5
        
        if len(df) < lookback_period + recent_period:
            return {'signal': False, 'desc': '', 'score': 0}
        
        # 前期高点（不包含最近5天）
        past_high = df['high'].iloc[-(lookback_period+recent_period):-recent_period].max()
        
        # 最近5天的最高价和最低价
        recent_high = df['high'].iloc[-recent_period:].max()
        recent_low = df['low'].iloc[-recent_period:].min()
        recent_close = df['close'].iloc[-1]
        
        # 检查是否突破前期高点（最近5天内突破）
        breakout_occurred = recent_high > past_high * 1.02  # 突破前期高点2%以上
        
        # 检查是否回踩（当前价格接近前期高点，但不跌破）
        retrace_to_support = recent_close >= past_high * 0.98 and recent_close <= past_high * 1.05
        
        # 检查成交量（突破时成交量是否放大）
        avg_volume = df['volume'].iloc[-(lookback_period+recent_period):-recent_period].mean()
        recent_volume = df['volume'].iloc[-recent_period:].mean()
        volume_expansion = recent_volume > avg_volume * 1.2  # 成交量放大20%以上
        
        # 综合判断
        if breakout_occurred and retrace_to_support:
            score = 25
            if volume_expansion:
                score += 10
                desc = f'突破回踩+放量(前高:{past_high:.2f}, 现价:{recent_close:.2f})'
            else:
                desc = f'突破回踩(前高:{past_high:.2f}, 现价:{recent_close:.2f})'
            
            return {'signal': True, 'desc': desc, 'score': score}
        
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_bottom_reversal(self, df: pd.DataFrame) -> dict:
        """
        底部反转策略: RSI和MACD双重确认
        """
        rsi = self.indicators.calc_rsi(df)
        dif, dea, macd_hist = self.indicators.calc_macd(df)
        
        rsi_reversal = rsi.iloc[-1] < 50 and rsi.iloc[-1] > rsi.iloc[-2]
        macd_reversal = dif.iloc[-1] > dea.iloc[-1]
        
        if rsi_reversal and macd_reversal:
            return {'signal': True, 'desc': 'RSI+MACD底部反转', 'score': 30}
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_trend_acceleration(self, df: pd.DataFrame) -> dict:
        """
        趋势加速策略: 均线多头+放量
        """
        ma_trend = self.strategy_ma_trend(df)
        volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(5).mean().iloc[-2]
        
        if ma_trend['signal'] and volume_ratio > 2:
            return {'signal': True, 'desc': f'均线多头+放量(量比:{volume_ratio:.1f})', 'score': 25}
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_strong_pullback(self, df: pd.DataFrame) -> dict:
        """
        强势股回调策略: 股价在20日线上方回调
        """
        ma20 = self.indicators.calc_ma(df, 20)
        is_strong = df['close'].iloc[-1] > ma20.iloc[-1]
        is_pullback = df['close'].iloc[-1] < df['close'].iloc[-2]

        if is_strong and is_pullback:
            return {'signal': True, 'desc': '强势股回调低吸', 'score': 20}
        return {'signal': False, 'desc': '', 'score': 0}
        
    def evaluate_all(self, df: pd.DataFrame, pe: float, peg: float, roe: float) -> dict:
        """
        综合评估所有策略
        """
        results = {}
        total_score = 0
        signals = []

        # 1. MA Trend
        res = self.strategy_ma_trend(df)
        results['ma_trend'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])

        # 2. MACD Trend
        res = self.strategy_macd_trend(df)
        results['macd_trend'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])
            
        # 3. Value Growth
        res = self.strategy_value_growth(pe, peg, roe)
        results['value_growth'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])
            
        # 4. Bottom Reversal
        res = self.strategy_bottom_reversal(df)
        results['bottom_reversal'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])
            
        # 5. Trend Acceleration
        res = self.strategy_trend_acceleration(df)
        results['trend_acceleration'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])
            
        # 6. Strong Pullback
        res = self.strategy_strong_pullback(df)
        results['strong_pullback'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])

        return {
            'total_score': total_score,
            'signals': signals,
            'details': results
        }
