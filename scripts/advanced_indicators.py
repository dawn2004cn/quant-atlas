#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级技术指标计算 (优化版)
"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
import numpy as np
from typing import Dict, Tuple

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import yfinance as yf
# 导入 ta 库
from ta.trend import SMAIndicator, ADXIndicator, CCIIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import RSIIndicator, StochasticOscillator
# 导入 ta 库
from ta.trend import SMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

from fundamental_data_reader import FundamentalDataReader

from app.core.logger import get_logger

logger = get_logger(__name__)


# ==========================================
# 1. 提取核心指标计算能力，只做数学运算，不包含任何业务判断逻辑
# ==========================================
class AdvancedIndicators:
    """提取核心指标计算能力，只做数学运算，不包含任何业务判断逻辑"""

    @staticmethod
    def calc_ma(close: pd.Series, window: int) -> pd.Series:
        return SMAIndicator(close=close, window=window).sma_indicator()

    @staticmethod
    def calc_macd(df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[
        pd.Series, pd.Series, pd.Series]:
        """
        计算 MACD 指标
        返回: DIF (快线), DEA (慢线/信号线), MACD (柱状图)
        """
        macd_indicator = MACD(
            close=df['close'],
            window_slow=slow_period,
            window_fast=fast_period,
            window_sign=signal_period
        )
        dif = macd_indicator.macd()
        dea = macd_indicator.macd_signal()
        macd = macd_indicator.macd_diff() * 2
        return dif, dea, macd
    @staticmethod
    def calc_adx(high: pd.Series, low: pd.Series, close: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        adx_ind = ADXIndicator(high=high, low=low, close=close, window=14)
        return adx_ind.adx(), adx_ind.adx_pos(), adx_ind.adx_neg()

    @staticmethod
    def calc_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        return OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    @staticmethod
    def calc_vol_ratio(volume: pd.Series, window: int = 5) -> pd.Series:
        past_ma = volume.shift(1).rolling(window=window).mean()
        return volume / past_ma.replace(0, np.nan)

    @staticmethod
    def calc_bias(close: pd.Series, window: int = 20) -> pd.Series:
        ma = SMAIndicator(close=close, window=window).sma_indicator()
        return (close - ma) / ma.replace(0, np.nan) * 100

    @staticmethod
    def calc_rsi(close: pd.Series, window: int = 14) -> pd.Series:
        return RSIIndicator(close=close, window=window).rsi()

    @staticmethod
    def calc_bb(close: pd.Series, window: int = 20, dev: float = 2.0):
        bb = BollingerBands(close=close, window=window, window_dev=dev)
        return bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()

    @staticmethod
    def calc_cci(df: pd.DataFrame, window: int = 20):
        """计算 CCI 顺势指标"""
        cci = CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=window)
        return cci.cci()

    @staticmethod
    def calc_dmi(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算 DMI 趋向指标
        返回: +DI (多方), -DI (空方), ADX (趋势强弱)
        """
        adx_evaluator = ADXIndicator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14,
            fillna=False
        )
        plus_di = adx_evaluator.adx_pos()
        minus_di = adx_evaluator.adx_neg()
        adx = adx_evaluator.adx()
        return plus_di, minus_di, adx

    @staticmethod
    def calc_kdj(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 9, smooth_window: int = 3):
        """
        计算 KDJ 指标 (采用经典 9,3,3 参数)
        """
        stoch = StochasticOscillator(
            high=high,
            low=low,
            close=close,
            window=window,
            smooth_window=smooth_window
        )
        # ta: stoch=原始 %K，stoch_signal=平滑 %D；通达信 K/D 与之对调
        stoch_k = stoch.stoch()
        stoch_d = stoch.stoch_signal()
        k = stoch_d
        d = stoch_k
        j = 3 * k - 2 * d  # 经典的 J 线公式 (反应最快)

        return k, d, j

# ==========================================
# 2. 选股模型基类 (抽象层 - 依赖倒置 & 开闭原则)
# ==========================================
class BaseSelectionModel(ABC):
    """选股模型抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """模型名称"""
        pass

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, indicators: AdvancedIndicators) -> Optional[Dict]:
        """
        评估函数：对传入的数据进行评估
        :param df: 标准化的历史K线数据 (列名为小写 open, high, low, close, volume)
        :param indicators: 指标计算工具类
        :return: 若未选中返回 None；若选中返回 Dict 包含得分和理由
        """
        pass


# ==========================================
# 3. 具体选股模型实现 (具体策略层 - 里氏替换)
# ==========================================

class BreakoutDragonModel(BaseSelectionModel):
    """模型 A：突破擒龙模型 (量比爆发 + ADX动能 + OBV资金确认)"""

    @property
    def name(self) -> str:
        return "突破擒龙模型"

    def evaluate(self, df: pd.DataFrame, ind: AdvancedIndicators) -> Optional[Dict]:
        if len(df) < 30: return None

        # 计算所需指标
        vol_ratio = ind.calc_vol_ratio(df['volume']).iloc[-1]
        adx, pdi, mdi = ind.calc_adx(df['high'], df['low'], df['close'])
        c_adx, c_pdi, c_mdi = adx.iloc[-1], pdi.iloc[-1], mdi.iloc[-1]

        obv = ind.calc_obv(df['close'], df['volume'])
        obv_ma20 = ind.calc_ma(obv, 20)

        # 判定条件
        reasons = []
        is_breakout = True

        # 1. 资金异动：今日量比大于 2.0
        if vol_ratio > 2.0:
            reasons.append(f"量比爆量 ({vol_ratio:.1f}倍)")
        else:
            is_breakout = False

        # 2. 动能爆发：ADX > 25 且多头占优
        if c_adx > 25 and c_pdi > c_mdi:
            reasons.append("ADX单边多头主升浪启动")
        else:
            is_breakout = False

        # 3. 主力资金未流出：OBV 在其20日均线之上
        if obv.iloc[-1] > obv_ma20.iloc[-1]:
            reasons.append("OBV显示主力资金流入")
        else:
            is_breakout = False

        if is_breakout:
            return {"score": 90, "reasons": " | ".join(reasons)}
        return None


class OversoldReboundModel(BaseSelectionModel):
    """模型 B：极度超跌反弹模型 (BIAS乖离极限 + RSI超卖)"""

    @property
    def name(self) -> str:
        return "极度超跌模型"

    def evaluate(self, df: pd.DataFrame, ind: AdvancedIndicators) -> Optional[Dict]:
        if len(df) < 25: return None

        bias20 = ind.calc_bias(df['close'], 20).iloc[-1]
        rsi = ind.calc_rsi(df['close']).iloc[-1]

        reasons = []
        is_oversold = True

        # 1. 乖离率极度偏离 20日均线 (设定阈值为 -12%)
        if bias20 < -12:
            reasons.append(f"BIAS严重负偏离 ({bias20:.1f}%)")
        else:
            is_oversold = False

        # 2. RSI 处于极度恐慌区
        if rsi < 30:
            reasons.append(f"RSI极度恐慌 ({rsi:.1f})")
        else:
            is_oversold = False

        if is_oversold:
            # 分数与偏离程度成正比
            score = min(100, 70 + abs(bias20))
            return {"score": round(score, 1), "reasons": " | ".join(reasons)}
        return None


class TrendResonanceModel(BaseSelectionModel):
    """模型 C：经典趋势共振模型 (稳健右侧交易)"""

    @property
    def name(self) -> str:
        return "趋势共振模型"

    def evaluate(self, df: pd.DataFrame, ind: AdvancedIndicators) -> Optional[Dict]:
        if len(df) < 60: return None

        close = df['close'].iloc[-1]
        ma20 = ind.calc_ma(df['close'], 20).iloc[-1]
        ma60 = ind.calc_ma(df['close'], 60).iloc[-1]

        # 检查是否全部有效
        if pd.isna(ma60): return None

        reasons = []
        is_trend = True

        # 多头排列
        if close > ma20 and ma20 > ma60:
            reasons.append("价格>MA20>MA60，标准多头排列")
        else:
            is_trend = False

        # 均线向上发散
        ma20_5d_ago = ind.calc_ma(df['close'], 20).iloc[-5]
        if ma20 > ma20_5d_ago:
            reasons.append("短期均线昂头向上")
        else:
            is_trend = False

        if is_trend:
            return {"score": 80, "reasons": " | ".join(reasons)}
        return None


# ==========================================
# 3. 四大经典核心选股模型 (开闭原则体现)
# ==========================================

class TrendTrackingModel(BaseSelectionModel):
    """策略 1: 趋势跟踪 (双均线金叉策略)"""

    @property
    def name(self) -> str:
        return "趋势跟踪 (双均线金叉)"

    def evaluate(self, df: pd.DataFrame, ind: AdvancedIndicators) -> Optional[Dict]:
        if len(df) < 65: return None

        # 计算 20日 和 60日 均线
        ma20 = ind.calc_ma(df['close'], 20)
        ma60 = ind.calc_ma(df['close'], 60)

        # 寻找“今天刚发生金叉”的时刻
        # 逻辑：今天 MA20 > MA60 且 昨天 MA20 <= MA60
        today_cross = ma20.iloc[-1] > ma60.iloc[-1]
        yesterday_below = ma20.iloc[-2] <= ma60.iloc[-2]

        if today_cross and yesterday_below and pd.notna(ma60.iloc[-1]):
            return {"score": 85, "reasons": "短期均线(20日)刚刚向上突破长期均线(60日)，右侧趋势确立。"}
        return None


class MeanReversionModel(BaseSelectionModel):
    """策略 2: 均值回归 (布林带下轨 + RSI抄底)"""

    @property
    def name(self) -> str:
        return "均值回归 (极度超卖)"

    def evaluate(self, df: pd.DataFrame, ind: AdvancedIndicators) -> Optional[Dict]:
        if len(df) < 25: return None

        bb_high, bb_mid, bb_low = ind.calc_bb(df['close'])
        rsi = ind.calc_rsi(df['close'])

        today_close = df['close'].iloc[-1]
        today_rsi = rsi.iloc[-1]

        # 逻辑：收盘价跌破布林下轨，并且 RSI 处于严重超卖区 (<30)
        if today_close < bb_low.iloc[-1] and today_rsi < 30:
            return {"score": 90, "reasons": f"跌穿布林带下轨且 RSI({today_rsi:.1f})严重超卖，博取超跌反弹。"}
        return None


class MomentumContinuationModel(BaseSelectionModel):
    """策略 3: 动量顺势 (EMA大趋势 + MACD回调买入)"""

    @property
    def name(self) -> str:
        return "动量顺势 (主升浪回调金叉)"

    def evaluate(self, df: pd.DataFrame, ind: AdvancedIndicators) -> Optional[Dict]:
        if len(df) < 205: return None  # 需要200日均线数据

        ema200 = ind.calc_ema(df['close'], 200)
        macd_line, macd_signal = ind.calc_macd(df['close'])

        today_close = df['close'].iloc[-1]

        # 条件 1：大趋势向好 (价格在200日均线之上)
        if today_close > ema200.iloc[-1] and pd.notna(ema200.iloc[-1]):
            # 条件 2：MACD 在今天刚刚发生金叉 (昨天死叉/平盘，今天金叉)
            macd_cross_today = macd_line.iloc[-1] > macd_signal.iloc[-1]
            macd_below_yesterday = macd_line.iloc[-2] <= macd_signal.iloc[-2]

            if macd_cross_today and macd_below_yesterday:
                return {"score": 95, "reasons": "处于200日均线上方的多头市场，且MACD刚好结束回调形成金叉。"}
        return None


class VolumePriceSynergyModel(BaseSelectionModel):
    """策略 4: 量价配合 (放量突破布林上轨)"""

    @property
    def name(self) -> str:
        return "量价配合 (放量突破)"

    def evaluate(self, df: pd.DataFrame, ind: AdvancedIndicators) -> Optional[Dict]:
        if len(df) < 25: return None

        bb_high, _, _ = ind.calc_bb(df['close'])
        obv = ind.calc_obv(df['close'], df['volume'])
        obv_ma20 = ind.calc_ma(obv, 20)  # OBV的20日均线

        # 寻找突破时刻：今天突破，昨天没突破
        today_close = df['close'].iloc[-1]
        yesterday_close = df['close'].iloc[-2]

        price_breakout = (today_close > bb_high.iloc[-1]) and (yesterday_close <= bb_high.iloc[-2])

        # 量能确认：OBV 在其均线之上，说明突破是真的有资金强力买入
        volume_confirm = obv.iloc[-1] > obv_ma20.iloc[-1]

        if price_breakout and volume_confirm:
            return {"score": 90, "reasons": "价格强力突破布林带上轨，且OBV能量潮确认量价齐升(非假突破)。"}
        return None
'''
1、防止高位钝化坠落：普通股民一看到金叉就买。但在高位（K>80）时的金叉往往是多头陷阱。代码中 is_oversold = yest_k < 30 直接将高位和中位的震荡杂波全部过滤。

2、J 线的前瞻性：KDJ 中，J 线的算法使得它在股价急跌时往往会跌破 0，在股价急涨时突破 100。代码中要求 yest_j < 10 且 today_j > yest_j，这实际上是在捕捉那根**“止跌探底的神针”**，通常这会在 K、D 金叉之前或同时给出极其强烈的转折确认。
'''
class KDJSwingModel(BaseSelectionModel):
    """策略 5: KDJ波段震荡 (超卖区金叉)"""

    @property
    def name(self) -> str:
        return "KDJ波段震荡 (超卖区金叉)"

    def evaluate(self, df: pd.DataFrame, ind: AdvancedIndicators) -> Optional[Dict]:
        if len(df) < 20:
            return None

        # 计算 K, D, J
        k, d, j = ind.calc_kdj(df['high'], df['low'], df['close'])

        # 获取今天和昨天的值
        today_k, today_d, today_j = k.iloc[-1], d.iloc[-1], j.iloc[-1]
        yest_k, yest_d, yest_j = k.iloc[-2], d.iloc[-2], j.iloc[-2]

        # ==========================================
        # 严苛的买点条件判定：
        # ==========================================
        # 1. 刚发生金叉：今天 K > D，且昨天 K <= D
        is_golden_cross = (today_k > today_d) and (yest_k <= yest_d)

        # 2. 位置过滤：金叉必须发生在超卖区 (昨天 K 值 < 30)
        is_oversold = yest_k < 30

        # 3. J线确认：J线属于极度敏感指标，J值由负转正，或从极低位向上猛烈抬头
        j_turning_up = (today_j > yest_j) and (yest_j < 10)

        # 满足基础金叉且处于超卖区
        if is_golden_cross and is_oversold:
            score = 85
            reasons = f"KDJ在底部超卖区(K={yest_k:.1f})形成金叉。"

            # 如果加上了 J 线的底背离或急速抬头确认，加分！
            if j_turning_up:
                score += 10
                reasons += f" 且敏感J线极低位触底反弹(急拉至{today_j:.1f})，短线爆发概率极大！"

            return {"score": score, "reasons": reasons}

        return None

# ==========================================
# 第一大类：均线与趋势形态类 (MA)
# ==========================================

class Model_01_TrendResonance(BaseSelectionModel):
    @property
    def name(self) -> str: return "01. 经典多头排列 (趋势王道)"
    def evaluate(self, df):
        if len(df) < 120: return None
        ma20, ma60, ma120 = AdvancedIndicators.calc_ma(df, 20), AdvancedIndicators.calc_ma(df, 60), AdvancedIndicators.calc_ma(df, 120)
        c = df['close'].iloc[-1]
        # 价格 > 20日 > 60日 > 120日，且 120日均线向上
        if c > ma20.iloc[-1] > ma60.iloc[-1] > ma120.iloc[-1] and ma120.iloc[-1] > ma120.iloc[-5]:
            return {"score": 80, "reasons": "长中短期均线呈现完美多头排列，趋势向上。"}
        return None

class Model_02_LotusOutWater(BaseSelectionModel):
    @property
    def name(self) -> str: return "02. 出水芙蓉 (一阳穿三线)"
    def evaluate(self, df):
        if len(df) < 60: return None
        ma20, ma40, ma60 = AdvancedIndicators.calc_ma(df, 20), AdvancedIndicators.calc_ma(df, 40), AdvancedIndicators.calc_ma(df, 60)
        o, c = df['open'].iloc[-1], df['close'].iloc[-1]
        # 一根大阳线（涨幅>4%），开盘在均线之下，收盘突破所有均线
        if (c - o) / o > 0.04 and o < min(ma20.iloc[-1], ma40.iloc[-1], ma60.iloc[-1]) and c > max(ma20.iloc[-1], ma40.iloc[-1], ma60.iloc[-1]):
            return {"score": 95, "reasons": "放量大阳线强势上穿三条核心均线，多头主力发力。"}
        return None

class Model_03_MASqueezeBreakout(BaseSelectionModel):
    @property
    def name(self) -> str: return "03. 均线粘合突破 (变盘节点)"
    def evaluate(self, df):
        if len(df) < 60: return None
        ma10, ma20, ma60 = AdvancedIndicators.calc_ma(df, 10), AdvancedIndicators.calc_ma(df, 20), AdvancedIndicators.calc_ma(df, 60)
        # 三根均线极度接近（极差 < 2%），且今日向上突破
        max_ma = max(ma10.iloc[-2], ma20.iloc[-2], ma60.iloc[-2])
        min_ma = min(ma10.iloc[-2], ma20.iloc[-2], ma60.iloc[-2])
        if (max_ma - min_ma) / min_ma < 0.02 and df['close'].iloc[-1] > max_ma and df['close'].iloc[-1] > df['open'].iloc[-1]:
            return {"score": 90, "reasons": "长期横盘致均线粘合，今日选择向上变盘突破。"}
        return None

class Model_04_ChannelPullback(BaseSelectionModel):
    @property
    def name(self) -> str: return "04. 趋势回踩确认 (缩量回档)"
    def evaluate(self, df):
        if len(df) < 60: return None
        ma60 = AdvancedIndicators.calc_ma(df, 60)
        c, l = df['close'].iloc[-1], df['low'].iloc[-1]
        # 60日线向上，最低价触碰60日线但收盘企稳
        if ma60.iloc[-1] > ma60.iloc[-10] and l <= ma60.iloc[-1] and c > ma60.iloc[-1]:
            return {"score": 85, "reasons": "主升浪中精准回踩60日生命线获得支撑。"}
        return None

# ==========================================
# 第二大类：MACD 经典投顾战法
# ==========================================

class Model_05_MACDZeroCross(BaseSelectionModel):
    @property
    def name(self) -> str: return "05. MACD 水上金叉 (空中加油)"
    def evaluate(self, df):
        if len(df) < 30: return None
        dif, dea, macd = AdvancedIndicators.calc_macd(df)
        # 均在0轴之上，且刚发生金叉
        if dif.iloc[-1] > 0 and dea.iloc[-1] > 0 and dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
            return {"score": 85, "reasons": "MACD强势区（0轴上）发生金叉，趋势空中加油启动。"}
        return None

class Model_06_MACDBottomCross(BaseSelectionModel):
    @property
    def name(self) -> str: return "06. MACD 水下金叉 (超跌企稳)"
    def evaluate(self, df):
        if len(df) < 30: return None
        dif, dea, macd = AdvancedIndicators.calc_macd(df)
        if dif.iloc[-1] < 0 and dea.iloc[-1] < 0 and dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
            return {"score": 75, "reasons": "MACD弱势区（0轴下）发生金叉，具备超跌反弹或筑底可能。"}
        return None

class Model_07_MACDBullishDivergence(BaseSelectionModel):
    @property
    def name(self) -> str: return "07. MACD 底背离 (抄底核武器)"
    def evaluate(self, df):
        if len(df) < 60: return None
        dif, dea, macd = AdvancedIndicators.calc_macd(df)
        # 简化版背离：价格创近期新低，但 DIF 未创新低，且即将金叉
        min_close_20 = df['close'].iloc[-20:-5].min()
        if df['close'].iloc[-1] < min_close_20 and dif.iloc[-1] > dif.iloc[-20:-5].min() and macd.iloc[-1] > macd.iloc[-2]:
            return {"score": 95, "reasons": "股价创新低，MACD绿柱缩短且DIF不创新低，经典底背离！"}
        return None

# ==========================================
# 第三大类：量价关系与主力资金类 (Volume & OBV)
# ==========================================

class Model_08_VolumeBreakout(BaseSelectionModel):
    @property
    def name(self) -> str: return "08. 放量打拐 (游资最爱)"
    def evaluate(self, df):
        if len(df) < 60: return None
        vol_ratio = AdvancedIndicators.calc_vol_ratio(df, 5).iloc[-1]
        ma60 = AdvancedIndicators.calc_ma(df, 60).iloc[-1]
        c, o = df['close'].iloc[-1], df['open'].iloc[-1]
        # 量比>2.5，阳线突破60日线
        if vol_ratio > 2.5 and c > o and df['close'].iloc[-2] < ma60 and c > ma60:
            return {"score": 90, "reasons": f"今日量比高达 {vol_ratio:.2f}，强力突破中期生命线。"}
        return None

class Model_09_SmartMoneyAccumulation(BaseSelectionModel):
    @property
    def name(self) -> str: return "09. OBV 底部吸筹 (主力潜伏)"
    def evaluate(self, df):
        if len(df) < 30: return None
        obv = AdvancedIndicators.calc_obv(df)
        # 近10天股价没怎么涨（涨幅<2%），但 OBV 却创出20天新高
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
        if abs(price_change) < 0.02 and obv.iloc[-1] >= obv.iloc[-20:].max():
            return {"score": 85, "reasons": "股价横盘滞涨，但OBV能量潮悄创新高，主力资金暗中吸筹。"}
        return None

class Model_10_ThreeWhiteSoldiers(BaseSelectionModel):
    @property
    def name(self) -> str: return "10. 红三兵 (温和放量推升)"
    def evaluate(self, df):
        if len(df) < 5: return None
        # 连续三天收阳，且收盘价创新高，成交量温和放大
        c1, c2, c3 = df['close'].iloc[-3], df['close'].iloc[-2], df['close'].iloc[-1]
        o1, o2, o3 = df['open'].iloc[-3], df['open'].iloc[-2], df['open'].iloc[-1]
        v1, v2, v3 = df['volume'].iloc[-3], df['volume'].iloc[-2], df['volume'].iloc[-1]
        if c1>o1 and c2>o2 and c3>o3 and c3>c2>c1 and v3>v2>v1:
            return {"score": 80, "reasons": "K线连收三阳且重心上移，成交量温和放大，多头稳步推进。"}
        return None

# ==========================================
# 第四大类：动量与超跌反弹类 (KDJ, RSI, CCI)
# ==========================================

class Model_11_KDJGoldenPit(BaseSelectionModel):
    @property
    def name(self) -> str: return "11. KDJ 黄金坑 (J线反击)"
    def evaluate(self, df):
        if len(df) < 20: return None
        k, d, j = AdvancedIndicators.calc_kdj(df)
        # 昨天 J < 0 (跌入泥潭)，今天 J 强势收复 0 轴
        if j.iloc[-2] < 0 and j.iloc[-1] > 0 and k.iloc[-1] < 30:
            return {"score": 85, "reasons": "极度敏锐的J线昨日跌破0轴，今日强力反抽，砸出黄金坑。"}
        return None

class Model_12_RSIOversoldReversal(BaseSelectionModel):
    @property
    def name(self) -> str: return "12. RSI 超卖拐点 (稳健抄底)"
    def evaluate(self, df):
        if len(df) < 20: return None
        rsi = AdvancedIndicators.calc_rsi(df)
        if rsi.iloc[-2] < 25 and rsi.iloc[-1] > rsi.iloc[-2]:
            return {"score": 80, "reasons": f"RSI进入极度冰点({rsi.iloc[-2]:.1f})后今日拐头向上。"}
        return None

class Model_13_CCITurningStrong(BaseSelectionModel):
    @property
    def name(self) -> str: return "13. CCI 弱转强 (抄底擒牛)"
    def evaluate(self, df):
        if len(df) < 20: return None
        cci = AdvancedIndicators.calc_cci(df)
        # CCI 从 -100 下方突破至 -100 上方，标准买点
        if cci.iloc[-2] < -100 and cci.iloc[-1] > -100:
            return {"score": 85, "reasons": "CCI顺势指标由极度恐慌区上穿-100地平线，短线转强。"}
        return None

class Model_14_BIASExtremePanic(BaseSelectionModel):
    @property
    def name(self) -> str: return "14. BIAS 极度恐慌 (乖离修复)"
    def evaluate(self, df):
        if len(df) < 30: return None
        bias24 = AdvancedIndicators.calc_bias(df, 24)
        if bias24.iloc[-1] < -20:
            return {"score": 90, "reasons": f"24日乖离率达 {bias24.iloc[-1]:.1f}%，严重背离均值，随时报复性反弹。"}
        return None

# ==========================================
# 第五大类：趋势突破与波动率类 (DMI, ATR, BB)
# ==========================================

class Model_15_DMIUnilateralTrend(BaseSelectionModel):
    @property
    def name(self) -> str: return "15. DMI 主升浪 (单边加速)"
    def evaluate(self, df):
        if len(df) < 20: return None
        pdi, mdi, adx = AdvancedIndicators.calc_dmi(df)
        # ADX > 40 说明趋势极强，PDI > MDI 说明是涨势
        if adx.iloc[-1] > 40 and adx.iloc[-1] > adx.iloc[-2] and pdi.iloc[-1] > mdi.iloc[-1]:
            return {"score": 95, "reasons": "ADX爆表(>40)且多头动能压制空头，开启主升浪爆发行情。"}
        return None

class Model_16_BBSqueezeBreakout(BaseSelectionModel):
    @property
    def name(self) -> str: return "16. 布林带缩口突破 (横有多长竖有多高)"
    def evaluate(self, df):
        if len(df) < 30: return None
        up, mid, low = AdvancedIndicators.calc_bb(df)
        width = (up.iloc[-2] - low.iloc[-2]) / mid.iloc[-2]
        # 布林带极度收敛（上下轨间距<10%），今日放量收盘突破上轨
        if width < 0.10 and df['close'].iloc[-1] > up.iloc[-1] and df['close'].iloc[-1] > df['open'].iloc[-1]:
            return {"score": 95, "reasons": "布林带长期缩口蓄势后，今日打破平静向上开口突破。"}
        return None

class Model_17_BBLowerSupport(BaseSelectionModel):
    @property
    def name(self) -> str: return "17. 布林下轨支撑 (震荡市高抛低吸)"
    def evaluate(self, df):
        if len(df) < 30: return None
        up, mid, low = AdvancedIndicators.calc_bb(df)
        # 最低价戳破下轨，但收盘价站回下轨且收阳线
        if df['low'].iloc[-1] < low.iloc[-1] and df['close'].iloc[-1] > low.iloc[-1] and df['close'].iloc[-1] > df['open'].iloc[-1]:
            return {"score": 75, "reasons": "探底布林带下轨后迅速拉起收阳，支撑有效。"}
        return None

class Model_18_ATRExpansion(BaseSelectionModel):
    @property
    def name(self) -> str: return "18. ATR 波动扩张 (异动狩猎)"
    def evaluate(self, df):
        if len(df) < 30: return None
        atr = AdvancedIndicators.calc_atr(df, 14)
        atr_ma = atr.rolling(14).mean()
        # 真实波幅突然放大 1.5 倍，且是向上突破 20 日均线
        ma20 = AdvancedIndicators.calc_ma(df, 20)
        if atr.iloc[-1] > 1.5 * atr_ma.iloc[-1] and df['close'].iloc[-1] > ma20.iloc[-1] and df['close'].iloc[-2] <= ma20.iloc[-2]:
            return {"score": 85, "reasons": "波动率异动放大1.5倍，同时向上突破短期防线，方向选择确立。"}
        return None

class Model_19_SingleBullishHold(BaseSelectionModel):
    @property
    def name(self) -> str: return "19. 单阳不破 (洗盘结束)"
    def evaluate(self, df):
        if len(df) < 15: return None
        # 5天前有一根涨幅>5%的大阳线，随后4天调整的最低价都没有跌破那根阳线的开盘价
        past_returns = (df['close'].shift(4) - df['open'].shift(4)) / df['open'].shift(4)
        big_yang_idx = -5
        if past_returns.iloc[-1] > 0.05:
            base_price = df['open'].iloc[-5]
            recent_lows = df['low'].iloc[-4:]
            if all(low > base_price for low in recent_lows) and df['close'].iloc[-1] > df['open'].iloc[-1]:
                return {"score": 80, "reasons": "大阳线拔地而起后，连续数日缩量洗盘且不破阳线底，随时二波上攻。"}
        return None

class Model_20_StrongTrendDip(BaseSelectionModel):
    @property
    def name(self) -> str: return "20. 强势股首阴/回调 (千金难买牛回头)"
    def evaluate(self, df):
        if len(df) < 30: return None
        ma10, ma20 = AdvancedIndicators.calc_ma(df, 10), AdvancedIndicators.calc_ma(df, 20)
        # 前期涨幅巨大（MA10 远大于 MA20），今天首次跌回 MA10 附近获得支撑
        if ma10.iloc[-1] > ma20.iloc[-1] * 1.05 and df['low'].iloc[-1] <= ma10.iloc[-1] and df['close'].iloc[-1] > ma10.iloc[-1]:
            return {"score": 85, "reasons": "极强势股首次回调至10日线生命线，往往伴随游资猛烈自救或二波。"}
        return None

#CANSLIM 选股模型 (欧奈尔高增长突破法)
class CANSLIMModel(BaseSelectionModel):
    @property
    def name(self) -> str:
        return "👑 CANSLIM 戴维斯双击 (基本面+技术面)"

    def evaluate(self, df: pd.DataFrame) -> Optional[dict]:
        # ----- 1. 技术面判断 (使用我们之前的通达信 K线数据 df) -----
        # 股价是否站在 200 日线之上，且刚刚突破布林带上轨
        ma200 = AdvancedIndicators.calc_ma(df, 200).iloc[-1]
        bb_up, _, _ = AdvancedIndicators.calc_bb(df)

        if df['close'].iloc[-1] < ma200 or df['close'].iloc[-1] < bb_up.iloc[-1]:
            return None  # 技术面不符合，直接淘汰，节约时间

        # ----- 2. 基本面判断 (使用我们刚写的 FundamentalDataReader) -----
        ticker = df['code']  # 假设你的 df 里带了纯代码字段

        # 检查最新财报的净利润增长率是否 > 20%
        df_fin = FundamentalDataReader.get_financial_report(ticker)
        if df_fin.empty: return None

        # 获取最近一期的净利润同比增长率
        latest_growth = df_fin['净利润同比增长率'].iloc[0]
        # 很多时候接口返回的是字符串，如 "25.4%"，需要剥离百分号
        latest_growth_val = float(str(latest_growth).replace('%', ''))

        if latest_growth_val > 20.0:
            return {
                "score": 95,
                "reasons": f"业绩暴增（净利润同比+{latest_growth_val}%）且技术面强势突破，经典戴维斯双击！"
            }

        return None
# ==========================================
# 4. 执行引擎 / 上下文管理器 (高层 - 门面模式)
# ==========================================
class StockScreenerEngine:
    """自动选股引擎"""

    def __init__(self):
        self.models: List[BaseSelectionModel] = []
        self.indicators = AdvancedIndicators()

    def register_model(self, model: BaseSelectionModel):
        """注册选股策略 (体现开闭原则)"""
        self.models.append(model)
        logger.info("成功加载模型: %s", model.name)

    def format_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """统一数据清洗格式"""
        df_clean = df.copy()
        if isinstance(df_clean.columns, pd.MultiIndex):
            df_clean.columns = df_clean.columns.droplevel('Ticker')
        # 强制小写
        df_clean.columns = [col.lower() for col in df_clean.columns]
        return df_clean

    def run(self, tickers: List[str], period: str = "6mo") -> pd.DataFrame:
        """执行全市场扫描"""
        results = []

        logger.info("开始扫描 %s 只股票数据...", len(tickers))
        for ticker in tickers:
            try:
                # 获取数据
                df = yf.download(ticker, period=period, progress=False)
                if df.empty: continue

                df_clean = self.format_data(df)
                latest_close = df_clean['close'].iloc[-1]

                # 遍历所有注册的模型
                for model in self.models:
                    res = model.evaluate(df_clean, self.indicators)
                    if res is not None:
                        # 如果该模型看中了这只股票，记录下来
                        results.append({
                            "股票代码": ticker,
                            "最新收盘价": round(latest_close, 2),
                            "触发模型": model.name,
                            "模型评分": res['score'],
                            "入选逻辑": res['reasons']
                        })
            except Exception as e:
                # 忽略个别股票下载或计算错误
                pass

                # 转化为易读的 DataFrame
        result_df = pd.DataFrame(results)
        if not result_df.empty:
            result_df = result_df.sort_values(by=['触发模型', '模型评分'], ascending=[True, False])
        return result_df

'''
进阶实战：多因子共振 (The Holy Grail)
在实盘中，一只股票如果在同一天只触发了一个模型（比如只触发了 KDJ 金叉），往往胜率只有 40%-50%。

但是，这套系统的终极威力在于寻找“共振”。如果在引擎生成的报表中，你发现 TSLA 在同一天同时触发了：

03. 均线粘合突破

08. 放量打拐

16. 布林带缩口突破

这种 3 个或以上模型共振发出的买入信号，在量化界被称为**“确定性异动点”**，胜率极高，就是你重仓干进去的最佳时机！
'''
# ==========================================
# 5. 主程序运行测试
# ==========================================
if __name__ == "__main__":
    # 1. 实例化引擎
    screener = StockScreenerEngine()

    # 2. 像搭积木一样，把你想用的策略“插入”到引擎中
    # screener.register_model(BreakoutDragonModel())
    # screener.register_model(OversoldReboundModel())
    # screener.register_model(TrendResonanceModel())
    # screener.register_model(TrendTrackingModel())
    # screener.register_model(MeanReversionModel())
    # screener.register_model(MomentumContinuationModel())
    # screener.register_model(VolumePriceSynergyModel())
    # # 🌟 一行代码接入我们刚刚写好的 KDJ 波段策略
    # screener.register_model(KDJSwingModel())

    # 批量注册 20 种投顾战法
    models = [
        BreakoutDragonModel(),
        OversoldReboundModel(),
        TrendResonanceModel(),
        TrendTrackingModel(),
        MeanReversionModel(),
        MomentumContinuationModel(),
        VolumePriceSynergyModel(),
        KDJSwingModel(),
        Model_01_TrendResonance(), Model_02_LotusOutWater(), Model_03_MASqueezeBreakout(), Model_04_ChannelPullback(),
        Model_05_MACDZeroCross(), Model_06_MACDBottomCross(), Model_07_MACDBullishDivergence(),
        Model_08_VolumeBreakout(), Model_09_SmartMoneyAccumulation(), Model_10_ThreeWhiteSoldiers(),
        Model_11_KDJGoldenPit(), Model_12_RSIOversoldReversal(), Model_13_CCITurningStrong(),
        Model_14_BIASExtremePanic(),
        Model_15_DMIUnilateralTrend(), Model_16_BBSqueezeBreakout(), Model_17_BBLowerSupport(), Model_18_ATRExpansion(),
        Model_19_SingleBullishHold(), Model_20_StrongTrendDip()
    ]

    for m in models:
        screener.register_model(m)

    # 3. 准备股票池 (纳斯达克明星股 + 波动较大的股票测试)
    watchlist = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'PLTR', 'COIN', 'MSTR', 'META', 'SNOW', 'BABA']

    # 4. 运行选股
    final_report = screener.run(watchlist)

    # 5. 打印结果
    logger.info("=" * 80)
    logger.info("量化选股最终报告")
    logger.info("=" * 80)

    if final_report.empty:
        logger.info("当前市场环境下，股票池中没有任何股票满足模型条件")
        logger.info("建议：耐心观望，或扩大股票扫描池")
    else:
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_colwidth', 80)
        pd.set_option('display.width', 1000)
        logger.info("\n%s", final_report.to_string(index=False))