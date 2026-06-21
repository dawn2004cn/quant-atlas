#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线选股策略集合
包含5大短线策略：
1. RSI短线 - 超短线RSI策略
2. MACD短线 - MACD金叉死叉
3. KDJ短线 - KDJ超买超卖
4. 布林突破 - 布林带突破
5. 放量突破 - 量价齐升
"""
import pandas as pd
from short_term_indicators import ShortTermIndicators

class ShortTermStrategies:
    def __init__(self):
        self.indicators = ShortTermIndicators()

    def strategy_rsi_short(self, df: pd.DataFrame) -> dict:
        """
        RSI短线策略: RSI < 30 超卖反弹
        """
        rsi = self.indicators.calc_rsi(df)
        rsi_now = rsi.iloc[-1]
        
        if rsi_now < 30:
            return {'signal': True, 'desc': f'RSI超卖 ({rsi_now:.1f})', 'score': 20}
        elif rsi_now < 40:
            return {'signal': True, 'desc': f'RSI偏低 ({rsi_now:.1f})', 'score': 10}
        
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_macd_short(self, df: pd.DataFrame) -> dict:
        """
        MACD短线策略: 金叉或即将金叉
        """
        dif, dea, macd_hist = self.indicators.calc_macd_short(df)
        result = self.indicators.detect_macd_cross(dif, dea, macd_hist)
        
        if result['golden_cross']:
            return {'signal': True, 'desc': 'MACD金叉', 'score': 15}
        elif result['signal'] == 'MACD翻红':
            return {'signal': True, 'desc': 'MACD柱翻红', 'score': 10}
        
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_kdj_short(self, df: pd.DataFrame) -> dict:
        """
        KDJ短线策略: 金叉且J值低位
        """
        k, d, j = self.indicators.calc_kdj(df)
        result = self.indicators.detect_kdj_cross(k, d, j)
        
        if result['golden_cross'] and result['j'] < 50:
             return {'signal': True, 'desc': f"KDJ金叉 (J={result['j']:.1f})", 'score': 20}
        elif result['oversold']:
             return {'signal': True, 'desc': f"KDJ超卖 (J={result['j']:.1f})", 'score': 15}
             
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_bollinger_breakout(self, df: pd.DataFrame) -> dict:
        """
        布林突破策略: 股价突破中轨或下轨反弹
        """
        upper, middle, lower = self.indicators.calc_bollinger(df)
        result = self.indicators.detect_bollinger_signal(df, upper, middle, lower)
        
        if result['signal'] == '下轨反弹':
            return {'signal': True, 'desc': f"布林下轨反弹", 'score': 15}
        elif result['signal'] == '中轨支撑':
             return {'signal': True, 'desc': "布林中轨支撑", 'score': 10}
             
        return {'signal': False, 'desc': '', 'score': 0}

    def strategy_volume_breakout(self, df: pd.DataFrame) -> dict:
        """
        放量突破策略: 量比>1.5且价格上涨
        """
        result = self.indicators.detect_volume_surge(df)
        
        if result['surge_type'] == '放量上涨':
             return {'signal': True, 'desc': f"放量突破 (量比{result['volume_ratio']:.1f})", 'score': 15}
        
        return {'signal': False, 'desc': '', 'score': 0}

    def evaluate_all(self, df: pd.DataFrame) -> dict:
        """
        综合评估所有策略
        """
        results = {}
        total_score = 0
        signals = []

        # 1. RSI
        res = self.strategy_rsi_short(df)
        results['rsi'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])

        # 2. MACD
        res = self.strategy_macd_short(df)
        results['macd'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])

        # 3. KDJ
        res = self.strategy_kdj_short(df)
        results['kdj'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])

        # 4. Bollinger
        res = self.strategy_bollinger_breakout(df)
        results['bollinger'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])
            
        # 5. Volume
        res = self.strategy_volume_breakout(df)
        results['volume'] = res
        if res['signal']:
            total_score += res['score']
            signals.append(res['desc'])

        return {
            'total_score': total_score,
            'signals': signals,
            'details': results
        }
