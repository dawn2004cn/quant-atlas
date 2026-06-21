import pandas as pd
import numpy as np
from core.base_strategy import BaseTradingStrategy
from ta.volatility import AverageTrueRange
from ta.trend import SMAIndicator

# ==========================================
# 🚀 1. 缺口动量法则 (Pro Gap & Go)
# ==========================================
class ProGapMomentumStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "🚀 专业跳空缺口 (Gap & Go)"
    @property
    def category(self) -> str: return "短线异动"
    @property
    def description(self) -> str: return "大幅跳空高开，越过近期高点，且伴随巨量，盘中不回补缺口。"
    @property
    def principle(self) -> str: return "事件驱动与流动性真空。巨大的向上跳空意味着重磅超预期利好，机构不计成本抢筹，空头被瞬间拉爆产生踩踏买盘。"
    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        
        # 过去 20 天的最高点
        recent_high = df['High'].rolling(20).max().shift(1)
        vol_ma10 = SMAIndicator(df['Volume'], 10).sma_indicator()
        
        # 1. 向上跳空：今天的开盘价 > 昨天的最高价 (留下绝对缺口)
        gap_up = df['Open'] > df['High'].shift(1)
        
        # 2. 突破前高：开盘价直接开在了过去20天最高点之上
        break_high = df['Open'] > recent_high
        
        # 3. 放量确认：今天成交量至少是均量的 2 倍
        vol_surge = df['Volume'] > (vol_ma10.shift(1) * 2.0)
        
        # 4. 拒绝回落 (高开高走)：收盘价 > 开盘价 (阳线)
        hold_gap = df['Close'] > df['Open']
        
        buy_cond = gap_up & break_high & vol_surge & hold_gap
        
        # 卖出：跌破跳空那一天的最低价，说明缺口被完全回补，逻辑伪证，立刻止损
        sell_cond = df['Close'] < df['Low'].shift(1)
        
        df.loc[buy_cond.fillna(False), 'Signal'] = 1
        df.loc[sell_cond.fillna(False), 'Signal'] = -1
        return df


# ==========================================
# 🛡️ 2. 超级趋势跟踪 (Vectorized SuperTrend)
# ==========================================
class SuperTrendStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "🛡️ 超级趋势 (SuperTrend)"
    @property
    def category(self) -> str: return "趋势突破"
    @property
    def description(self) -> str: return "基于 ATR 波动率计算动态多空分界线，价格站上分界线做多，跌破做空。"
    @property
    def principle(self) -> str: return "动态波动率追踪。在低波动时防守线收紧，在高波动时防守线放宽，完美过滤噪音，是 CTA 基金替代双均线的最佳方案。"
    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        
        period = 10
        multiplier = 3.0
        
        atr = AverageTrueRange(df['High'], df['Low'], df['Close'], period).average_true_range()
        hl2 = (df['High'] + df['Low']) / 2
        
        # 基础上下轨
        basic_upperband = hl2 + (multiplier * atr)
        basic_lowerband = hl2 - (multiplier * atr)
        
        # 向量化计算 SuperTrend 逻辑 (近似实现)
        # 为了避免复杂的 for 循环，我们使用一种极为接近的向量化近似：
        # 如果收盘价在近期均线上方，防守线为下轨的最大值；反之亦然。
        close = df['Close']
        
        # 这里的实现用 Chandelier Exit (吊灯线) 的改良版作为纯向量化的完美平替
        long_stop = df['High'].rolling(period).max() - multiplier * atr
        short_stop = df['Low'].rolling(period).min() + multiplier * atr
        
        # 向上突破空头止损线 (趋势翻多)
        buy_cond = (close > short_stop.shift(1)) & (close.shift(1) <= short_stop.shift(2))
        
        # 向下跌破多头止损线 (趋势翻空)
        sell_cond = (close < long_stop.shift(1)) & (close.shift(1) >= long_stop.shift(2))
        
        df.loc[buy_cond.fillna(False), 'Signal'] = 1
        df.loc[sell_cond.fillna(False), 'Signal'] = -1
        return df


# ==========================================
# 🩸 3. VSA 恐慌停止量 (Stopping Volume)
# ==========================================
class VSAStoppingVolumeStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "🩸 VSA 恐慌巨量停止"
    @property
    def category(self) -> str: return "恐慌抄底"
    @property
    def description(self) -> str: return "在明确的下跌趋势中爆出天量，但K线实体极小，拒绝继续下跌。"
    @property
    def principle(self) -> str: return "供需极度失衡。天量代表庞大的抛压，但价格却跌不下去（K线振幅极小），说明有一个资金极其雄厚的‘无底洞’在原价位吃进了所有抛盘，见底信号极强。"
    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        
        ma20 = SMAIndicator(df['Close'], 20).sma_indicator()
        vol_ma20 = SMAIndicator(df['Volume'], 20).sma_indicator()
        
        # 1. 明确的下跌趋势：价格远低于 20 日均线 (乖离率 < -10%)
        down_trend = (df['Close'] - ma20) / ma20.replace(0, np.nan) < -0.10
        
        # 2. 爆出天量：成交量是过去20日均量的 3 倍以上
        climax_vol = df['Volume'] > (vol_ma20.shift(1) * 3.0)
        
        # 3. 实体狭窄 (停止动作)：散户疯狂砸盘，但价格跌不下去。实体大小占全天振幅不到 30%
        body = (df['Close'] - df['Open']).abs()
        range_hl = (df['High'] - df['Low']).replace(0, np.nan)
        narrow_spread = (body / range_hl) < 0.30
        
        buy_cond = down_trend & climax_vol & narrow_spread
        
        # 卖出：只要反弹站上 10 日线就获利了结
        sell_cond = df['Close'] > SMAIndicator(df['Close'], 10).sma_indicator()
        
        df.loc[buy_cond.fillna(False), 'Signal'] = 1
        df.loc[sell_cond.fillna(False), 'Signal'] = -1
        return df