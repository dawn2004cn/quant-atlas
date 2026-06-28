"""Pure model definitions for trend breakout strategies.

Contains all strategy classes from the original trend_breakout.py.
Each strategy inherits from BaseTradingStrategy and implements
pure pandas/numpy computation with zero infrastructure dependencies.
"""

import numpy as np
import pandas as pd
from ta.trend import MACD, ADXIndicator, EMAIndicator, IchimokuIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands, DonchianChannel, KeltnerChannel

from ..core.base_strategy import BaseTradingStrategy


class MAStrategy(BaseTradingStrategy):
    """MA 双均线交叉策略"""

    @property
    def name(self) -> str: return "MA 双均线交叉策略"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "短周期移动平均线（20日）向上穿越长周期移动平均线（60日）。"

    @property
    def principle(self) -> str: return "短期成本突破长期成本，代表市场动能实质性向上反转，多头主导市场。"

    def get_start_idx(self) -> int: return 60

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['Signal'] = 0
        ma20 = SMAIndicator(df['Close'], 20).sma_indicator()
        ma60 = SMAIndicator(df['Close'], 60).sma_indicator()

        buy_cond = (ma20 > ma60) & (ma20.shift(1) <= ma60.shift(1))
        sell_cond = (ma20 < ma60) & (ma20.shift(1) >= ma60.shift(1))

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ----------------- 【类别一：趋势与均线】 -----------------
class DualMovingAverageStrategy(BaseTradingStrategy):
    """策略 1: 双均线交叉策略 (趋势跟踪)"""

    @property
    def name(self) -> str:
        return "01. 双均线交叉策略"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "短期均线（如20日）由下向上穿越长期均线（如60日），形成黄金交叉。"

    @property
    def principle(self) -> str: return "短期成本突破长期成本。短线资金的买入意愿已经强过长线资金的沉淀成本，代表市场动能发生实质性向上反转。"

    def __init__(self, short_window=20, long_window=60):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['SMA_short'] = SMAIndicator(close=df['Close'], window=self.short_window).sma_indicator()
        df['SMA_long'] = SMAIndicator(close=df['Close'], window=self.long_window).sma_indicator()

        df['Signal'] = 0
        buy_cond = (df['SMA_short'] > df['SMA_long']) & (df['SMA_short'].shift(1) <= df['SMA_long'].shift(1))
        sell_cond = (df['SMA_short'] < df['SMA_long']) & (df['SMA_short'].shift(1) >= df['SMA_long'].shift(1))

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        return 60


class MultiMAResonanceStrategy(BaseTradingStrategy):
    """策略 2: 经典多头排列 (趋势王道)"""

    @property
    def name(self) -> str: return "02. 经典多头排列"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "短期、中期、长期均线呈阶梯状向上排列（如 20>60>120），且长期均线抬头向上。"

    @property
    def principle(self) -> str: return "全周期多头共识。所有周期的参与者都在获利，上方没有任何套牢盘的抛压阻力，是趋势投资阻力最小的方向。"

    def get_start_idx(self) -> int: return 120

    def horizon_tags(self) -> list[str]:
        return ["mid", "long"]

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ma20 = SMAIndicator(df['Close'], 20).sma_indicator()
        ma60 = SMAIndicator(df['Close'], 60).sma_indicator()
        ma120 = SMAIndicator(df['Close'], 120).sma_indicator()
        df['Signal'] = 0

        buy_cond = (df['Close'] > ma20) & (ma20 > ma60) & (ma60 > ma120) & (ma120 > ma120.shift(5))
        sell_cond = df['Close'] < ma20  # 跌破20日线止盈/止损

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class LotusOutWaterStrategy(BaseTradingStrategy):
    """策略 3: 出水芙蓉 (一阳穿三线)"""

    @property
    def name(self) -> str: return "03. 出水芙蓉"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "长期横盘或均线密集后，一根放量大阳线向上贯穿多条中长期均线。"

    @property
    def principle(self) -> str: return "成本一致性原理。均线粘合代表各周期散户成本趋于一致，放量大阳线是主力吹响冲锋号角、打破筹码平衡的明确信号。"

    def get_start_idx(self) -> int: return 60

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ma20 = SMAIndicator(df['Close'], 20).sma_indicator()
        ma40 = SMAIndicator(df['Close'], 40).sma_indicator()
        ma60 = SMAIndicator(df['Close'], 60).sma_indicator()

        max_ma = pd.concat([ma20, ma40, ma60], axis=1).max(axis=1)
        min_ma = pd.concat([ma20, ma40, ma60], axis=1).min(axis=1)

        df['Signal'] = 0
        big_yang = (df['Close'] - df['Open']) / df['Open'] > 0.04
        cross_three = (df['Open'] < min_ma) & (df['Close'] > max_ma)

        buy_cond = big_yang & cross_three
        sell_cond = df['Close'] < ma20
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class MASqueezeBreakoutStrategy(BaseTradingStrategy):
    """策略 4: 均线粘合突破"""

    @property
    def name(self) -> str: return "04. 均线粘合突破"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "多条均线极度接近（极差<2%），经过长期横盘后，价格放量向上突破均线束。"

    @property
    def principle(self) -> str: return "时间换空间。长时间的横盘震荡导致所有持仓者的成本无限趋于一致，筹码高度集中。一旦主力选择向上点火，极易形成暴烈的单边行情。"

    def get_start_idx(self) -> int: return 60

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ma10 = SMAIndicator(df['Close'], 10).sma_indicator()
        ma20 = SMAIndicator(df['Close'], 20).sma_indicator()
        ma60 = SMAIndicator(df['Close'], 60).sma_indicator()

        max_ma = np.maximum.reduce([ma10, ma20, ma60])
        min_ma = np.minimum.reduce([ma10, ma20, ma60])

        df['Signal'] = 0
        squeeze = pd.Series((max_ma - min_ma) / np.where(min_ma == 0, np.nan, min_ma) < 0.02, index=df.index)
        buy_cond = squeeze.shift(1) & (df['Close'] > max_ma) & (df['Close'] > df['Open'])
        sell_cond = df['Close'] < ma20

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class EMAMACDContinuationStrategy(BaseTradingStrategy):
    """策略 6: EMA顺势 MACD 回调"""

    @property
    def name(self) -> str: return "06. EMA顺势MACD回调"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "在EMA120长期上升趋势中，寻找MACD金叉的回调买入点。"

    @property
    def principle(self) -> str: return "趋势续航理论。长期均线定义大方向，MACD金叉识别调整结束、主升浪回归的买点。"

    def get_start_idx(self) -> int: return 120

    def horizon_tags(self) -> list[str]:
        return ["mid", "long"]

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ema120 = EMAIndicator(df['Close'], 120).ema_indicator()
        macd = MACD(df['Close'])
        dif, dea = macd.macd(), macd.macd_signal()

        df['Signal'] = 0
        macd_gold = (dif > dea) & (dif.shift(1) <= dea.shift(1))
        macd_dead = (dif < dea) & (dif.shift(1) >= dea.shift(1))

        buy_cond = (df['Close'] > ema120) & macd_gold
        sell_cond = macd_dead | (df['Close'] < ema120)

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class MACDZeroCrossStrategy(BaseTradingStrategy):
    """策略 7: MACD 水上金叉 (空中加油)"""

    @property
    def name(self) -> str: return "07. MACD 水上金叉"

    @property
    def category(self) -> str: return "动量成长"

    @property
    def description(self) -> str: return "MACD的快慢线（DIF和DEA）在零轴上方发生黄金交叉。"

    @property
    def principle(self) -> str: return "动量加速度翻转。快线是对价格近期变动的敏感反应，快线上穿慢线代表近期的做多加速度已经超越了历史平均水平。"

    def get_start_idx(self) -> int: return 35

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        macd = MACD(df['Close'])
        dif, dea = macd.macd(), macd.macd_signal()
        df['Signal'] = 0

        buy_cond = (dif > 0) & (dea > 0) & (dif > dea) & (dif.shift(1) <= dea.shift(1))
        sell_cond = (dif < dea) & (dif.shift(1) >= dea.shift(1))
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class DMITrendStrategy(BaseTradingStrategy):
    """策略 10: DMI 主升浪"""

    @property
    def name(self) -> str: return "10. DMI 主升浪"

    @property
    def category(self) -> str: return "动量成长"

    @property
    def description(self) -> str: return "ADX指标大于40且持续上升，同时多方力量(+DI)压制空方力量(-DI)。"

    @property
    def principle(self) -> str: return "极强单边趋势确认。ADX不反映方向只反映强度，当ADX爆表时说明市场已经彻底陷入一边倒的疯狂，此时任何做空或猜顶行为都是极其危险的。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        adx_ind = ADXIndicator(df['High'], df['Low'], df['Close'], 14)
        adx, pdi, mdi = adx_ind.adx(), adx_ind.adx_pos(), adx_ind.adx_neg()
        df['Signal'] = 0

        buy_cond = (adx > 40) & (adx > adx.shift(1)) & (pdi > mdi)
        sell_cond = pdi < mdi
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class VolumeBreakoutStrategy(BaseTradingStrategy):
    """底部放量突破策略"""

    @property
    def name(self) -> str: return "底部放量突破策略"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "长期横盘后，爆出远超近期均量(>2.5倍)的巨量，并突破20日最高点。"

    @property
    def principle(self) -> str: return "量在价先。底部爆量绝对是机构不计成本抢筹的行为，是主升浪开启的冲锋号。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        vol_ma20 = SMAIndicator(df['Volume'], 20).sma_indicator()
        recent_high = df['High'].rolling(20).max().shift(1)

        buy_cond = (df['Volume'] > vol_ma20.shift(1) * 2.5) & (df['Close'] > recent_high)
        sell_cond = df['Close'] < SMAIndicator(df['Close'], 10).sma_indicator()

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ----------------- 【类别三：量价与资金】 -----------------
class VolBBBreakoutStrategy(BaseTradingStrategy):
    """策略 11: 放量突破布林上轨"""

    @property
    def name(self) -> str: return "11. 放量突破布林上轨"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "长期横盘或均线密集后，一根放量大阳线向上贯穿多条中长期均线。"

    @property
    def principle(self) -> str: return "成本一致性原理。均线粘合代表各周期散户成本趋于一致，放量大阳线是主力吹响冲锋号角、打破筹码平衡的明确信号。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        bb = BollingerBands(df['Close'], window=20)
        up, mid = bb.bollinger_hband(), bb.bollinger_mavg()
        vol_ma5 = SMAIndicator(df['Volume'], 5).sma_indicator()
        df['Signal'] = 0

        buy_cond = (df['Close'] > up) & (df['Close'].shift(1) <= up.shift(1)) & (df['Volume'] > vol_ma5.shift(1) * 2)
        sell_cond = df['Close'] < mid
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class VolMABreakoutStrategy(BaseTradingStrategy):
    """策略 25: 放量突破生命线"""

    @property
    def name(self) -> str: return "25. 放量突破生命线"

    @property
    def category(self) -> str: return "短线异动"

    @property
    def description(self) -> str: return "成交量大于过去5日平均成交量的一倍以上，且当日K线强势贯穿中期生命线（如20日或60日均线）。"

    @property
    def principle(self) -> str: return "量价齐升破冰。底部均线密集区的突破如果不带量，大概率是假突破（诱多）。只有成倍放大的成交量，才能证明是主力真金白银的建仓扫货。"

    def get_start_idx(self) -> int: return 60

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ma60 = SMAIndicator(df['Close'], 60).sma_indicator()
        vol_ma5 = SMAIndicator(df['Volume'], 5).sma_indicator()
        df['Signal'] = 0

        buy_cond = (df['Volume'] > vol_ma5.shift(1) * 2.5) & (df['Close'] > ma60) & (df['Open'] < ma60)
        sell_cond = df['Close'] < SMAIndicator(df['Close'], 20).sma_indicator()
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class ThreeWhiteSoldiersStrategy(BaseTradingStrategy):
    """策略 13: 红三兵 (温和放量)"""

    @property
    def name(self) -> str: return "13. 红三兵"

    @property
    def category(self) -> str: return "动量成长"

    @property
    def description(self) -> str: return "连续三个交易日收出阳线，且每日收盘价均创出新高，成交量伴随温和放大。"

    @property
    def principle(self) -> str: return "多方稳健推进。连续的红三兵表明买盘不仅强烈而且持久，多头步步为营，未见明显抛压，是健康主升浪开启的早期标志。"

    def get_start_idx(self) -> int: return 10

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        is_yang = df['Close'] > df['Open']
        three_yang = is_yang & is_yang.shift(1) & is_yang.shift(2)
        price_up = (df['Close'] > df['Close'].shift(1)) & (df['Close'].shift(1) > df['Close'].shift(2))
        vol_up = (df['Volume'] > df['Volume'].shift(1)) & (df['Volume'].shift(1) > df['Volume'].shift(2))

        buy_cond = three_yang & price_up & vol_up
        sell_cond = df['Close'] < SMAIndicator(df['Close'], 10).sma_indicator()
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class TAUStrategy(BaseTradingStrategy):
    """TAU 时序加权动量策略"""

    @property
    def name(self) -> str: return "TAU 时序加权动量策略"

    @property
    def category(self) -> str: return "动量成长"

    @property
    def description(self) -> str: return "基于时间指数衰减加权的动量策略，捕捉近期刚刚爆发的最强上涨动能。"

    @property
    def principle(self) -> str: return "动量时间衰减理论。近期发生的放量大涨对未来趋势的影响远大于半年前。赋予近期高权重进行测算。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        returns = df['Close'].pct_change()
        tau_momentum = returns.ewm(span=10, adjust=False).mean() * 100

        buy_cond = (tau_momentum > 2.0) & (tau_momentum > tau_momentum.shift(1))
        sell_cond = tau_momentum < 0

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class NR7BreakoutStrategy(BaseTradingStrategy):
    """托比·克拉贝尔 NR7 窄幅爆发"""

    @property
    def name(self) -> str: return "托比·克拉贝尔 NR7 窄幅爆发"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "昨日振幅是过去7天内最小的(NR7)，今日价格突破昨日最高点。"

    @property
    def principle(self) -> str: return "波动率收缩极值。极致的死寂（NR7）必然酝酿着多空平衡的瞬间打破和单边行情的井喷。"

    def get_start_idx(self) -> int: return 10

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        daily_range = df['High'] - df['Low']
        is_nr7 = daily_range == daily_range.rolling(7).min()

        buy_cond = is_nr7.shift(1) & (df['Close'] > df['High'].shift(1))
        sell_cond = is_nr7.shift(1) & (df['Close'] < df['Low'].shift(1))

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class TTMSqueezeBreakoutStrategy(BaseTradingStrategy):
    """
    策略 27: TTM Squeeze 挤压突破模型 (高爆发战法)
    逻辑：布林带收缩进肯特纳通道后再次释放，配合动能爆发。
    """

    @property
    def name(self) -> str: return "🌟 TTM Squeeze 挤压爆发模型"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "布林带完全收缩进肯特纳通道内部后，再次向上开口扩张，且动量指标为正。"

    @property
    def principle(self) -> str: return "波动率均值回归定理。市场总是在极度平静（波动率收缩）和极度狂热（波动率扩张）之间循环。挤压解除的瞬间是动能释放的最佳做多点。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        bb = BollingerBands(df['Close'], window=20, window_dev=2.0)
        bb_upper, bb_lower = bb.bollinger_hband(), bb.bollinger_lband()

        kc = KeltnerChannel(df['High'], df['Low'], df['Close'], window=20, window_atr=1.5)
        kc_upper, kc_lower = kc.keltner_channel_hband(), kc.keltner_channel_lband()

        momentum = df['Close'] - df['Close'].rolling(20).mean()

        df['Signal'] = 0

        squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
        squeeze_fired_up = squeeze_on.shift(1) & (~squeeze_on) & (momentum > 0)
        sell_cond = momentum < 0

        df.loc[squeeze_fired_up, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class TurtleTradingStrategy(BaseTradingStrategy):
    """
    策略 28: 海龟交易法则 (唐奇安通道突破)
    逻辑：突破 20 日最高点做多，跌破 10 日最低点平仓。
    """

    @property
    def name(self) -> str: return "🐢 海龟法则 (唐奇安通道突破)"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "向上突破过去20日的最高点时无脑做多，跌破10日最低点止损。"

    @property
    def principle(self) -> str: return "趋势惯性定理。放弃预测市场，纯粹依靠价格创出新高来证明上涨趋势的存在，利用大数法则赚取长尾利润。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        dc_20 = DonchianChannel(df['High'], df['Low'], df['Close'], window=20)
        dc_10 = DonchianChannel(df['High'], df['Low'], df['Close'], window=10)

        upper_20 = dc_20.donchian_channel_hband()
        lower_10 = dc_10.donchian_channel_lband()

        df['Signal'] = 0

        buy_cond = df['Close'] > upper_20.shift(1)
        sell_cond = df['Close'] < lower_10.shift(1)

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class GuppyMMAStrategy(BaseTradingStrategy):
    """
    策略 29: GMMA 顾比复合均线趋势共振
    逻辑：短期均线束整体上穿长期均线束。
    """

    @property
    def name(self) -> str: return "🐉 顾比复合均线 (GMMA) 共振"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "短期均线束整体上穿长期均线束（GMMA金叉），代表散户与机构达成趋势共识。"

    @property
    def principle(self) -> str: return "顾比复合均线理论。通过短期和长期两组均线的位置关系，识别'投机者'与'投资者'的共振，从而捕捉高确定性的趋势启动。"

    def get_start_idx(self) -> int: return 65

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        short_emas = [EMAIndicator(df['Close'], w).ema_indicator() for w in [3, 5, 8, 10, 12, 15]]
        long_emas = [EMAIndicator(df['Close'], w).ema_indicator() for w in [30, 35, 40, 45, 50, 60]]

        short_min = pd.concat(short_emas, axis=1).min(axis=1)
        long_max = pd.concat(long_emas, axis=1).max(axis=1)

        df['Signal'] = 0

        buy_cond = (short_min > long_max) & (short_min.shift(1) <= long_max.shift(1))

        short_max = pd.concat(short_emas, axis=1).max(axis=1)
        long_min = pd.concat(long_emas, axis=1).min(axis=1)
        sell_cond = short_max < long_min

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class IchimokuCloudStrategy(BaseTradingStrategy):
    """
    策略 30: 一目均衡表 (云图突破)
    逻辑：价格穿越先行跨度组成的云层之上，且短期线金叉长期线。
    """

    @property
    def name(self) -> str: return "☁️ 一目均衡表 (云层突破)"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "价格向上脱离先行跨度组成的云层（Kumo），且转换线金叉基准线。"

    @property
    def principle(self) -> str: return "时间序列的阻力测算。云层代表了过去一段资金的历史平均沉淀成本，脱离云层意味着上方的历史套牢盘已被全部消化。"

    def get_start_idx(self) -> int: return 55

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ichi = IchimokuIndicator(df['High'], df['Low'], visual=False)

        tenkan = ichi.ichimoku_conversion_line()
        kijun = ichi.ichimoku_base_line()

        senkou_a = ichi.ichimoku_a()
        senkou_b = ichi.ichimoku_b()

        cloud_top = np.maximum(senkou_a, senkou_b)

        df['Signal'] = 0

        price_above_cloud = df['Close'] > cloud_top
        cross_up = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))

        buy_cond = price_above_cloud & cross_up
        sell_cond = df['Close'] < cloud_top

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class BBSqueezeStrategy(BaseTradingStrategy):
    """策略 21: 布林带缩口突破"""

    @property
    def name(self) -> str: return "21. 布林带缩口突破"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "布林带上下轨间距极度收窄（开口率<10%），随后一根放量K线向上冲破布林带上轨。"

    @property
    def principle(self) -> str: return "波动压缩爆发定律。'横有多长，竖有多高'。极致的波动收敛意味着多空博弈的静默期，静默期被向上打破往往宣告着一轮新趋势的诞生。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        bb = BollingerBands(df['Close'], window=20)
        up, mid, low = bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()
        df['Signal'] = 0

        squeeze = (up - low) / mid < 0.10
        buy_cond = squeeze.shift(1) & (df['Close'] > up) & (df['Close'].shift(1) <= up.shift(1))
        sell_cond = df['Close'] < mid
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class ATRExpansionStrategy(BaseTradingStrategy):
    """策略 23: ATR 波动扩张"""

    @property
    def name(self) -> str: return "23. ATR 波动扩张"

    @property
    def category(self) -> str: return "短线异动"

    @property
    def description(self) -> str: return "真实波动幅度(ATR)突然放大超过其均值的1.5倍，同时股价放量向上突破近期防线。"

    @property
    def principle(self) -> str: return "波动率异变嗅探。长期的死水微澜突然掀起惊涛骇浪（ATR暴增），结合向上突破，这是重磅利好消息刺激或大资金强力进场的铁证。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        atr = AverageTrueRange(df['High'], df['Low'], df['Close'], 14).average_true_range()
        atr_ma = SMAIndicator(atr, 14).sma_indicator()
        ma20 = SMAIndicator(df['Close'], 20).sma_indicator()
        df['Signal'] = 0

        buy_cond = (atr > atr_ma.shift(1) * 1.5) & (df['Close'] > ma20) & (df['Close'].shift(1) <= ma20.shift(1))
        sell_cond = df['Close'] < ma20
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ==========================================
# 🏮 11. 亚历山大·埃尔德 吊灯止损反转突破 (Chandelier Exit)
# ==========================================
class ChandelierExitStrategy(BaseTradingStrategy):
    """
    流派：动态波动率通道 (ATR 极致运用)
    逻辑：吊灯止损本是用来逃顶的，但用来做"反转做多"威力同样惊人。
    将过去 22 天的最高点，往下悬挂 3 倍的 ATR 形成"吊灯止损线"。
    一旦空头行情结束，股价强力向上突破了这根吊灯线，说明空头被彻底歼灭，反转主升浪开启。
    """

    @property
    def name(self) -> str: return "🏮 吊灯止损空翻多突破"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "股价放量向上突破由 22日最高价 - 3倍ATR 构成的动态吊灯防守线。"

    @property
    def principle(self) -> str: return "空头防线总崩塌。吊灯线是完美的波动率动态防守线，一旦该线被多方强力攻克，说明空方最后的阵地失守，反转的大趋势已经不可阻挡。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0

        highest_22 = df['High'].rolling(22).max()
        atr_22 = AverageTrueRange(df['High'], df['Low'], df['Close'], 22).average_true_range()

        chandelier_exit = highest_22 - 3 * atr_22

        breakout = (df['Close'] > chandelier_exit) & (df['Close'].shift(1) <= chandelier_exit.shift(1))
        buy_cond = breakout
        sell_cond = df['Close'] < chandelier_exit

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ==========================================
# 🐊 9. 比尔·威廉姆斯 (Bill Williams) - 鳄鱼苏醒法则
# ==========================================
class AlligatorAwakeningStrategy(BaseTradingStrategy):
    """
    流派：混沌操作法 (分形几何与非线性动力学)
    逻辑：比尔·威廉姆斯认为市场 70%到80%的时间在睡觉，只有20%的时间有行情。
    鳄鱼指标由三条特殊平移的平滑均线组成（唇、齿、颚）。
    当三条线交织在一起时，鳄鱼在睡觉（不要交易）。
    当唇线上穿齿线和颚线，且三线向上张开时，鳄鱼苏醒开始吃肉（进场）。
    """

    @property
    def name(self) -> str: return "🐊 比尔·威廉姆斯 鳄鱼苏醒"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "鳄鱼三线（向右平移的非线性均线）从长期紧密缠绕的'睡眠状态'，突然向上张开大嘴（唇线>齿线>颚线）。"

    @property
    def principle(self) -> str: return "分形几何的混沌破局。市场从无序的随机漫步（三线交织）中觉醒，分形结构被打破，顺势进入单边吞噬行情的进餐期。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0

        typical_price = (df['High'] + df['Low']) / 2

        jaw = SMAIndicator(typical_price, 13).sma_indicator().shift(8)
        teeth = SMAIndicator(typical_price, 8).sma_indicator().shift(5)
        lips = SMAIndicator(typical_price, 5).sma_indicator().shift(3)

        max_line = np.maximum.reduce([jaw, teeth, lips])
        min_line = np.minimum.reduce([jaw, teeth, lips])
        sleeping = pd.Series(((max_line - min_line) / np.where(min_line == 0, np.nan, min_line)) < 0.015, index=jaw.index)

        awakening = (lips > teeth) & (teeth > jaw)
        buy_cond = sleeping.shift(1) & awakening
        sell_cond = lips < teeth

        df.loc[buy_cond.fillna(False), 'Signal'] = 1
        df.loc[sell_cond.fillna(False), 'Signal'] = -1
        return df


class CANSLIMModelStrategy(BaseTradingStrategy):
    """
    策略: CANSLIM 欧奈尔高增长突破法 (技术面+基本面共振)
    技术面：价格处于 200日均线 之上的长牛走势，且近期放量突破布林带上轨（杯柄突破）。
    基本面：最新季度净利润同比增长率 > 20% (C/A法则)。
    """

    @property
    def name(self) -> str:
        return "26. CANSLIM 戴维斯双击模型"

    @property
    def category(self) -> str:
        return "动量成长"

    @property
    def description(self) -> str:
        return "基本面净利润增速>20%，且技术面上放量突破布林带上轨。"

    @property
    def principle(self) -> str:
        return "基本面与资金面的共振。高增长提供估值底座，放量突破代表机构资金正在加速建仓，容易形成戴维斯双击的超级牛股。"

    def get_start_idx(self) -> int:
        return 200

    def horizon_tags(self) -> list[str]:
        return ["long"]

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        要求输入的 DataFrame 中除了 OHLCV，还需包含提前获取好的基本面列：
        'net_profit_growth' (净利润同比增长率，例如 25.4 代表 25.4%)
        如果你无法将基本面合并到 df 中，也可以在代码中设定为默认值或忽略。
        """
        ma200 = SMAIndicator(close=df['Close'], window=200).sma_indicator()
        ma50 = SMAIndicator(close=df['Close'], window=50).sma_indicator()

        bb = BollingerBands(close=df['Close'], window=20, window_dev=2.0)
        bb_up = bb.bollinger_hband()

        vol_ma5 = SMAIndicator(close=df['Volume'], window=5).sma_indicator()

        df['Signal'] = 0

        tech_bull_market = (df['Close'] > ma50) & (ma50 > ma200)
        tech_breakout = (df['Close'] > bb_up) & (df['Close'].shift(1) <= bb_up.shift(1))
        tech_volume_surge = df['Volume'] > (vol_ma5.shift(1) * 1.5)

        if 'net_profit_growth' in df.columns:
            fund_high_growth = df['net_profit_growth'] > 20.0
        else:
            fund_high_growth = pd.Series(True, index=df.index)

        buy_cond = tech_bull_market & tech_breakout & tech_volume_surge & fund_high_growth
        sell_cond = df['Close'] < ma50

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1

        return df


__all__ = [
    'MAStrategy',
    'DualMovingAverageStrategy',
    'MultiMAResonanceStrategy',
    'LotusOutWaterStrategy',
    'MASqueezeBreakoutStrategy',
    'EMAMACDContinuationStrategy',
    'MACDZeroCrossStrategy',
    'DMITrendStrategy',
    'VolumeBreakoutStrategy',
    'VolBBBreakoutStrategy',
    'VolMABreakoutStrategy',
    'ThreeWhiteSoldiersStrategy',
    'TAUStrategy',
    'NR7BreakoutStrategy',
    'TTMSqueezeBreakoutStrategy',
    'TurtleTradingStrategy',
    'GuppyMMAStrategy',
    'IchimokuCloudStrategy',
    'BBSqueezeStrategy',
    'ATRExpansionStrategy',
    'ChandelierExitStrategy',
    'AlligatorAwakeningStrategy',
    'CANSLIMModelStrategy',
]
