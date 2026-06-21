#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级中长线技术指标
"""
import pandas as pd
from typing import Dict, Tuple

# 导入 ta 库
from ta.trend import SMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange


class AdvancedLongTermIndicators:
    """高级中长线技术指标"""

    def calc_ma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        计算移动平均线
        """
        return SMAIndicator(close=df['close'], window=period).sma_indicator()

    def calc_macd(self, df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算MACD指标
        """
        macd_indicator = MACD(close=df['close'], window_slow=slow_period, window_fast=fast_period, window_sign=signal_period)
        dif = macd_indicator.macd()
        dea = macd_indicator.macd_signal()
        macd = macd_indicator.macd_diff() * 2  # 保持与原实现一致
        return dif, dea, macd

    def calc_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算RSI指标
        """
        return RSIIndicator(close=df['close'], window=period).rsi()

    def calc_dmi(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        1. 计算 DMI 指标 (使用 ta 库)

        DMI (Directional Movement Index) 趋向指标包含三条线：
        - +DI (Plus Directional Indicator): 多方动能线
        - -DI (Minus Directional Indicator): 空方动能线
        - ADX (Average Directional Index): 趋势强弱线
        """
        # 实例化 ta 库的 ADX 评价器，标准金融参数 window 设为 14
        adx_evaluator = ADXIndicator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14,
            fillna=False
        )

        # 提取三根核心线
        plus_di = adx_evaluator.adx_pos()
        minus_di = adx_evaluator.adx_neg()
        adx = adx_evaluator.adx()

        return plus_di, minus_di, adx

    def calc_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算ATR指标
        """
        return AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=period).average_true_range()

    def analyze_dmi_signal(self, plus_di: float, minus_di: float, adx: float) -> Dict:
        """
        2. 分析截面 DMI 信号

        金融逻辑：
        - ADX > 25：代表市场有明确的单边趋势。
        - ADX < 20：代表市场处于横盘震荡，此时 DI 线的交叉大部分是“假信号”。
        - +DI > -DI：多头占优。
        - +DI < -DI：空头占优。
        """
        signal = 'hold'
        strength = 'none'

        # 判断趋势的强度
        trend_active = adx > 25

        # 核心多空判定
        if plus_di > minus_di:
            signal = 'buy'
            strength = 'strong' if trend_active else 'weak'
        elif minus_di > plus_di:
            signal = 'sell'
            strength = 'strong' if trend_active else 'weak'

        # 震荡市过滤器 (极重要的防坑机制)
        if adx < 20:
            signal = 'hold'
            strength = 'ranging'  # 震荡市，不具备交易价值

        return {
            'signal': signal,
            'strength': strength,
            'adx_value': round(adx, 2),
            'pdi': round(plus_di, 2),
            'mdi': round(minus_di, 2)
        }

    def optimize_signal_trigger(self, dmi_analysis: Dict) -> Dict:
        """
        3. 优化信号触发 (综合评分器)

        将原始信号转换为带有分数(Score)的具体操作建议。
        分数区间：[-100, 100]。>80为强做多，<-80为强做空。
        """
        score = 0
        reasons = []
        decision = '观望'

        signal = dmi_analysis.get('signal', 'hold')
        strength = dmi_analysis.get('strength', 'none')
        adx_val = dmi_analysis.get('adx_value', 0)

        # 基础打分与归因
        if signal == 'buy':
            reasons.append("多方力量(+DI)主导市场。")
            score += 50
            if strength == 'strong':
                reasons.append(f"ADX 高达 {adx_val}，上涨单边趋势确立！")
                score += 40  # 总分 90
            elif strength == 'weak':
                reasons.append(f"但 ADX 仅为 {adx_val}，缺乏强劲动能，可能为震荡反弹。")

        elif signal == 'sell':
            reasons.append("空方力量(-DI)主导市场。")
            score -= 50
            if strength == 'strong':
                reasons.append(f"ADX 高达 {adx_val}，恐慌下跌趋势确立！")
                score -= 40  # 总分 -90
            elif strength == 'weak':
                reasons.append(f"但 ADX 仅为 {adx_val}，跌势暂未完全放大。")

        elif strength == 'ranging':
            reasons.append(f"ADX 低于 20 (当前 {adx_val})，市场陷入无趋势泥潭，指标已钝化。")

        # 根据最终分数制定交易策略决策
        if score >= 80:
            decision = '强烈买入 (重仓)'
        elif 0 < score < 80:
            decision = '轻仓试多 (建底仓)'
        elif score <= -80:
            decision = '清仓逃顶 (或做空)'
        elif -80 < score < 0:
            decision = '减仓防守 (止盈止损)'
        else:
            decision = '空仓观望'

        return {
            'decision': decision,
            'reasons': reasons,
            'score': score,
            'signal_count': 1  # 扩展接口，若未来接入MACD，此计数可累加
        }

    # ==========================================
    # 核心：多因子综合打分系统
    # ==========================================
    def calculate_comprehensive_score(self, df: pd.DataFrame) -> Dict:
        """
        基于最新一天的截面数据，计算多因子综合得分 (-100 到 +100)
        """
        # 1. 提取最新一天的所有指标数值
        current_close = df['close'].iloc[-1]

        # 均线 (长线趋势判断)
        ma50 = self.calc_ma(df, 50).iloc[-1]
        ma200 = self.calc_ma(df, 200).iloc[-1]

        # MACD (中线动能)
        dif, dea, macd_hist = self.calc_macd(df)
        c_dif, c_dea, c_macd = dif.iloc[-1], dea.iloc[-1], macd_hist.iloc[-1]

        # RSI (超买超卖识别)
        rsi = self.calc_rsi(df).iloc[-1]

        # DMI (趋势强度)
        pdi, mdi, adx = self.calc_dmi(df)
        c_pdi, c_mdi, c_adx = pdi.iloc[-1], mdi.iloc[-1], adx.iloc[-1]

        # ATR (波动率用于风控计算)
        atr = self.calc_atr(df).iloc[-1]

        # 2. 开始打分归因 (满分100)
        score = 0
        reasons = []

        # -- 因子 1: 均线趋势 (权重 30 分) --
        if current_close > ma200 and ma50 > ma200:
            score += 30
            reasons.append("✅ 均线多头: 价格站上200日线且50日线上穿，长线向好 (+30分)")
        elif current_close < ma200:
            score -= 30
            reasons.append("❌ 均线空头: 价格跌破200日牛熊分界线，长线看跌 (-30分)")

        # -- 因子 2: MACD 动能 (权重 20 分) --
        if c_dif > c_dea and c_dif > 0:
            score += 20
            reasons.append("✅ MACD多头: 处于零轴上方且金叉，动能强劲 (+20分)")
        elif c_dif < c_dea and c_dif < 0:
            score -= 20
            reasons.append("❌ MACD空头: 零轴下方死叉，动能衰竭 (-20分)")

        # -- 因子 3: RSI 强弱 (权重 20 分) --
        if 50 <= rsi <= 70:
            score += 20
            reasons.append(f"✅ RSI强势: RSI={rsi:.1f}，处于多头健康上升区 (+20分)")
        elif rsi > 70:
            score -= 10  # 虽然涨但超买，扣分防追高
            reasons.append(f"⚠️ RSI超买: RSI={rsi:.1f}，存在短期回调风险 (-10分)")
        elif rsi < 30:
            score += 10  # 严重超卖，有抄底反弹预期
            reasons.append(f"💡 RSI超卖: RSI={rsi:.1f}，具备短线跌深反弹可能 (+10分)")

        # -- 因子 4: DMI 趋势确认 (权重 30 分) --
        if c_pdi > c_mdi and c_adx > 25:
            score += 30
            reasons.append(f"✅ DMI爆发: ADX={c_adx:.1f}>25且多方占优，单边主升浪确认 (+30分)")
        elif c_pdi < c_mdi and c_adx > 25:
            score -= 30
            reasons.append(f"❌ DMI暴跌: ADX={c_adx:.1f}>25且空方占优，单边主跌浪确认 (-30分)")
        elif c_adx < 20:
            reasons.append(f"💤 DMI钝化: ADX={c_adx:.1f}<20，市场处于无聊震荡期 (0分)")

        # 3. 评级与建议
        rating = "观望"
        if score >= 80:
            rating = "⭐⭐⭐⭐⭐ 强烈买入"
        elif score >= 50:
            rating = "⭐⭐⭐ 建议建仓"
        elif score <= -50:
            rating = "☠️ 强烈卖出"

        # 基于 ATR 给出的防守建议
        stop_loss_price = current_close - (2 * atr)

        return {
            "score": score,
            "rating": rating,
            "close_price": current_close,
            "stop_loss": stop_loss_price,
            "reasons": reasons
        }
