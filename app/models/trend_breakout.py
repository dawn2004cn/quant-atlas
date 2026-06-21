import pandas as pd
import numpy as np
from ..core.base_strategy import BaseTradingStrategy  # 假设基类放在 core 文件夹下
from ta.trend import SMAIndicator, EMAIndicator, MACD, IchimokuIndicator, ADXIndicator
from ta.volatility import BollingerBands, KeltnerChannel, DonchianChannel, AverageTrueRange


class MAStrategy(BaseTradingStrategy):
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

    # 19. 双均线交叉策略 (DualMovingAverageStrategy)
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
        # 计算指标
        df['SMA_short'] = SMAIndicator(close=df['Close'], window=self.short_window).sma_indicator()
        df['SMA_long'] = SMAIndicator(close=df['Close'], window=self.long_window).sma_indicator()

        # 生成信号
        df['Signal'] = 0
        # 金叉买入
        buy_cond = (df['SMA_short'] > df['SMA_long']) & (df['SMA_short'].shift(1) <= df['SMA_long'].shift(1))
        # 死叉卖出
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

    # 20. 经典多头排列 (MultiMAResonanceStrategy)
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

    # 6. 出水芙蓉 / 放量打拐 / 均线粘合突破
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

    # 21. 均线粘合突破 (MASqueezeBreakoutStrategy)
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

        # 🚀 优化 1：使用 np.maximum.reduce 替换 pd.concat，性能暴增
        max_ma = np.maximum.reduce([ma10, ma20, ma60])
        min_ma = np.minimum.reduce([ma10, ma20, ma60])

        df['Signal'] = 0
		# 🚀 优化 2：除零保护
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

    # 26. MACD 水上金叉 (MACDZeroCrossStrategy) / MACD 水下金叉 (MACDBottomCrossStrategy)
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

    # 27. DMI 主升浪 (DMITrendStrategy)
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

        # 爆量突破
        buy_cond = (df['Volume'] > vol_ma20.shift(1) * 2.5) & (df['Close'] > recent_high)
        # 跌破突破阳线的开盘价止损
        sell_cond = df['Close'] < SMAIndicator(df['Close'], 10).sma_indicator()

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ----------------- 【类别三：量价与资金】 -----------------
# 6. 出水芙蓉 / 放量打拐 / 均线粘合突破 类别 ：趋势突破
class VolBBBreakoutStrategy(BaseTradingStrategy):
    """策略 11: 放量突破布林上轨"""

    @property
    def name(self) -> str: return "11. 放量突破布林上轨"

    # 6. 出水芙蓉 / 放量打拐 / 均线粘合突破
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

    # 28. 放量突破生命线 (VolMABreakoutStrategy)
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

    # 30. 红三兵 (ThreeWhiteSoldiersStrategy)
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
        # 计算动量：当日收益率
        returns = df['Close'].pct_change()
        # TAU 核心：使用 ewm (指数加权移动平均) 赋予近期更高的权重
        tau_momentum = returns.ewm(span=10, adjust=False).mean() * 100

        buy_cond = (tau_momentum > 2.0) & (tau_momentum > tau_momentum.shift(1))
        sell_cond = tau_momentum < 0

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class NR7BreakoutStrategy(BaseTradingStrategy):
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
"""
1. TTM Squeeze (约翰·卡特 挤压突破模型)
原理：
这是华尔街极度追捧的波动率策略。
当布林带（Bollinger Bands）完全收缩进肯特纳通道（Keltner Channel）内部时，市场处于“极度压缩”的积蓄期（Squeeze On）。
当布林带重新扩张穿出肯特纳通道，且动能向上时，往往会爆发史诗级的主升浪。
"""
class TTMSqueezeBreakoutStrategy(BaseTradingStrategy):
    """
    策略 27: TTM Squeeze 挤压突破模型 (高爆发战法)
    逻辑：布林带收缩进肯特纳通道后再次释放，配合动能爆发。
    """

    @property
    def name(self) -> str: return "🌟 TTM Squeeze 挤压爆发模型"

    # 2. TTM Squeeze 挤压爆发模型 (TTMSqueezeBreakoutStrategy)
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "布林带完全收缩进肯特纳通道内部后，再次向上开口扩张，且动量指标为正。"

    @property
    def principle(self) -> str: return "波动率均值回归定理。市场总是在极度平静（波动率收缩）和极度狂热（波动率扩张）之间循环。挤压解除的瞬间是动能释放的最佳做多点。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # 1. 计算 20日布林带
        bb = BollingerBands(df['Close'], window=20, window_dev=2.0)
        bb_upper, bb_lower = bb.bollinger_hband(), bb.bollinger_lband()

        # 2. 计算 20日肯特纳通道 (Keltner Channel)
        kc = KeltnerChannel(df['High'], df['Low'], df['Close'], window=20, window_atr=1.5)
        kc_upper, kc_lower = kc.keltner_channel_hband(), kc.keltner_channel_lband()

        # 3. 动能震荡指标 (简化版 Momentum)
        momentum = df['Close'] - df['Close'].rolling(20).mean()

        df['Signal'] = 0

        # 状态判定：Squeeze On (布林带完全被包在肯特纳通道内)
        squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)

        # 买入条件：昨天还在挤压，今天挤压解除(向上爆发)，且动能为正
        squeeze_fired_up = squeeze_on.shift(1) & (~squeeze_on) & (momentum > 0)

        # 卖出条件：动能衰竭由正转负，或向下爆破
        sell_cond = momentum < 0

        df.loc[squeeze_fired_up, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

"""
原理：统治华尔街几十年的经典趋势跟踪策略。核心逻辑：不预测未来，只跟随趋势。创 20 日新高无脑买入，跌破 10 日新低坚决止损。
"""
class TurtleTradingStrategy(BaseTradingStrategy):
    """
    策略 28: 海龟交易法则 (唐奇安通道突破)
    逻辑：突破 20 日最高点做多，跌破 10 日最低点平仓。
    """

    @property
    def name(self) -> str: return "🐢 海龟法则 (唐奇安通道突破)"

    # 3. 海龟交易法则 (TurtleTradingStrategy)
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "向上突破过去20日的最高点时无脑做多，跌破10日最低点止损。"

    @property
    def principle(self) -> str: return "趋势惯性定理。放弃预测市场，纯粹依靠价格创出新高来证明上涨趋势的存在，利用大数法则赚取长尾利润。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # 计算 20日 和 10日 唐奇安通道
        dc_20 = DonchianChannel(df['High'], df['Low'], df['Close'], window=20)
        dc_10 = DonchianChannel(df['High'], df['Low'], df['Close'], window=10)

        # 唐奇安通道的上轨即为过去N天的最高价，下轨为最低价
        upper_20 = dc_20.donchian_channel_hband()
        lower_10 = dc_10.donchian_channel_lband()

        df['Signal'] = 0

        # 买入：今日收盘价 突破 昨天的20日最高点
        buy_cond = df['Close'] > upper_20.shift(1)

        # 卖出：今日收盘价 跌破 昨天的10日最低点
        sell_cond = df['Close'] < lower_10.shift(1)

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

"""
原理：利用两组指数移动平均线（短期组和长期组）的相互关系来揭示主力资金和散户资金的行为。
当短期组像绳子一样收束并整体上穿长期组时，代表机构主力大举建仓。
"""

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
    def principle(self) -> str: return "顾比复合均线理论。通过短期和长期两组均线的位置关系，识别‘投机者’与‘投资者’的共振，从而捕捉高确定性的趋势启动。"

    def get_start_idx(self) -> int: return 65

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # 短期散户线束 (3, 5, 8, 10, 12, 15)
        short_emas = [EMAIndicator(df['Close'], w).ema_indicator() for w in [3, 5, 8, 10, 12, 15]]
        # 长期主力线束 (30, 35, 40, 45, 50, 60)
        long_emas = [EMAIndicator(df['Close'], w).ema_indicator() for w in [30, 35, 40, 45, 50, 60]]

        # 获取短期组的最小值 和 长期组的最大值
        short_min = pd.concat(short_emas, axis=1).min(axis=1)
        long_max = pd.concat(long_emas, axis=1).max(axis=1)

        df['Signal'] = 0

        # 买入：短期组的“最弱线”都涨过了长期组的“最强线”，发生彻头彻尾的共振金叉
        buy_cond = (short_min > long_max) & (short_min.shift(1) <= long_max.shift(1))

        # 卖出：短期线束跌入长期线束内部（短期最强线跌破长期最弱线）
        short_max = pd.concat(short_emas, axis=1).max(axis=1)
        long_min = pd.concat(long_emas, axis=1).min(axis=1)
        sell_cond = short_max < long_min

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

"""
原理：日本流传最广的量化交易系统。
它通过“云层（Kumo）”将阻力位和支撑位可视化。当价格突破云层，且转换线金叉基准线时，顺势做多的胜率极高。
"""
class IchimokuCloudStrategy(BaseTradingStrategy):
    """
    策略 30: 一目均衡表 (云图突破)
    逻辑：价格穿越先行跨度组成的云层之上，且短期线金叉长期线。
    """

    @property
    def name(self) -> str: return "☁️ 一目均衡表 (云层突破)"

    # 5. 一目均衡表云层突破 (IchimokuCloudStrategy)
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "价格向上脱离先行跨度组成的云层（Kumo），且转换线金叉基准线。"

    @property
    def principle(self) -> str: return "时间序列的阻力测算。云层代表了过去一段资金的历史平均沉淀成本，脱离云层意味着上方的历史套牢盘已被全部消化。"

    def get_start_idx(self) -> int: return 55

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ichi = IchimokuIndicator(df['High'], df['Low'], visual=False)

        # 转换线 (Tenkan-sen, 类似于短期均线) 和 基准线 (Kijun-sen, 类似于长期均线)
        tenkan = ichi.ichimoku_conversion_line()
        kijun = ichi.ichimoku_base_line()

        # 先行跨度 A 和 B 组成了“云层 (Kumo)”
        senkou_a = ichi.ichimoku_a()
        senkou_b = ichi.ichimoku_b()

        # 云层顶部和底部
        cloud_top = np.maximum(senkou_a, senkou_b)
        cloud_bottom = np.minimum(senkou_a, senkou_b)

        df['Signal'] = 0

        # 买入：价格在云层上方(脱离苦海) 且 转换线金叉基准线
        price_above_cloud = df['Close'] > cloud_top
        cross_up = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))

        buy_cond = price_above_cloud & cross_up

        # 卖出：价格跌回云层内部或下方
        sell_cond = df['Close'] < cloud_top

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class BBSqueezeStrategy(BaseTradingStrategy):
    """策略 21: 布林带缩口突破"""

    @property
    def name(self) -> str: return "21. 布林带缩口突破"

    # 24. 布林带缩口突破 (BBSqueezeStrategy)
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "布林带上下轨间距极度收窄（开口率<10%），随后一根放量K线向上冲破布林带上轨。"

    @property
    def principle(self) -> str: return "波动压缩爆发定律。“横有多长，竖有多高”。极致的波动收敛意味着多空博弈的静默期，静默期被向上打破往往宣告着一轮新趋势的诞生。"

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

    # 38. ATR 波动扩张 (ATRExpansionStrategy)
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
    逻辑：吊灯止损本是用来逃顶的，但用来做“反转做多”威力同样惊人。
    将过去 22 天的最高点，往下悬挂 3 倍的 ATR 形成“吊灯止损线”。
    一旦空头行情结束，股价强力向上突破了这根吊灯线，说明空头被彻底歼灭，反转主升浪开启。
    """

    @property
    def name(self) -> str: return "🏮 吊灯止损空翻多突破"

    # 39. 吊灯止损空翻多突破 (ChandelierExitStrategy)
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "股价放量向上突破由 22日最高价 - 3倍ATR 构成的动态吊灯防守线。"

    @property
    def principle(self) -> str: return "空头防线总崩塌。吊灯线是完美的波动率动态防守线，一旦该线被多方强力攻克，说明空方最后的阵地失守，反转的大趋势已经不可阻挡。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0

        # 计算 22 日最高价 和 22 日 ATR
        highest_22 = df['High'].rolling(22).max()
        atr_22 = AverageTrueRange(df['High'], df['Low'], df['Close'], 22).average_true_range()

        # 吊灯线 (多头防守线/空头止损线) = 最高价 - 3倍ATR
        chandelier_exit = highest_22 - 3 * atr_22

        # 突破做多：长期在吊灯线下方的票，今天放量站上吊灯线
        breakout = (df['Close'] > chandelier_exit) & (df['Close'].shift(1) <= chandelier_exit.shift(1))

        buy_cond = breakout

        # 卖出：再次跌破吊灯线
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

    # 40. 鳄鱼苏醒 (AlligatorAwakeningStrategy)
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "鳄鱼三线（向右平移的非线性均线）从长期紧密缠绕的‘睡眠状态’，突然向上张开大嘴（唇线>齿线>颚线）。"

    @property
    def principle(self) -> str: return "分形几何的混沌破局。市场从无序的随机漫步（三线交织）中觉醒，分形结构被打破，顺势进入单边吞噬行情的进餐期。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0

        # 鳄鱼三线 (典型价 (H+L)/2 的平滑移动平均，并向右平移)
        typical_price = (df['High'] + df['Low']) / 2

        # 颚线 (Jaw): 13周期SMA，向未来平移 8
        jaw = SMAIndicator(typical_price, 13).sma_indicator().shift(8)
        # 齿线 (Teeth): 8周期SMA，向未来平移 5
        teeth = SMAIndicator(typical_price, 8).sma_indicator().shift(5)
        # 唇线 (Lips): 5周期SMA，向未来平移 3
        lips = SMAIndicator(typical_price, 5).sma_indicator().shift(3)

        # 鳄鱼睡眠状态：三线紧密缠绕 (极差极小)
        max_line = np.maximum.reduce([jaw, teeth, lips])
        min_line = np.minimum.reduce([jaw, teeth, lips])
        sleeping = pd.Series(((max_line - min_line) / np.where(min_line == 0, np.nan, min_line)) < 0.015, index=jaw.index)

        # 鳄鱼张嘴 (苏醒做多)：唇线 > 齿线 > 颚线，且昨天还在睡觉
        awakening = (lips > teeth) & (teeth > jaw)
        buy_cond = sleeping.shift(1) & awakening

        # 鳄鱼闭嘴 (吃饱离场)：唇线向下跌破齿线
        sell_cond = lips < teeth

        df.loc[buy_cond.fillna(False), 'Signal'] = 1
        df.loc[sell_cond.fillna(False), 'Signal'] = -1
        return df
"""
CANSLIM（欧奈尔高增长突破法）是量化界极负盛名的**“基本面 + 技术面”双重共振策略**。

要在我们纯向量化的 BaseTradingStrategy 架构下实现 CANSLIM，我们需要处理一个特殊的难题：基本面数据（如季度净利润增长率）的频率是“季频/年频”，而 K 线数据是“日频”。
因此，在生成每日的 1, 0, -1 交易信号时，我们需要将基本面数据**前向填充（forward-fill）**或作为额外的过滤条件传入。
"""

class CANSLIMModelStrategy(BaseTradingStrategy):
    """
    策略: CANSLIM 欧奈尔高增长突破法 (技术面+基本面共振)
    技术面：价格处于 200日均线 之上的长牛走势，且近期放量突破布林带上轨（杯柄突破）。
    基本面：最新季度净利润同比增长率 > 20% (C/A法则)。
    """
    @property
    def name(self) -> str:
        return "26. CANSLIM 戴维斯双击模型"

    # 4. CANSLIM 戴维斯双击 (CANSLIMModelStrategy)
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
        return 200  # 需要计算 200 日均线，预热期必须大于 200

    def horizon_tags(self) -> list[str]:
        return ["long"]

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        要求输入的 DataFrame 中除了 OHLCV，还需包含提前获取好的基本面列：
        'net_profit_growth' (净利润同比增长率，例如 25.4 代表 25.4%)
        如果你无法将基本面合并到 df 中，也可以在代码中设定为默认值或忽略。
        """
        # --- 1. 计算技术指标 ---
        # 长线趋势：200日均线
        ma200 = SMAIndicator(close=df['Close'], window=200).sma_indicator()
        # 中线趋势：50日均线
        ma50 = SMAIndicator(close=df['Close'], window=50).sma_indicator()

        # 突破形态：20日布林带上轨
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2.0)
        bb_up = bb.bollinger_hband()
        bb_mid = bb.bollinger_mavg()

        # 量能异动：5日均量
        vol_ma5 = SMAIndicator(close=df['Volume'], window=5).sma_indicator()

        df['Signal'] = 0

        # --- 2. 组装买入条件 (Buy) ---

        # 技术面条件 A：牛市背景 (收盘价 > 50日线 > 200日线)
        tech_bull_market = (df['Close'] > ma50) & (ma50 > ma200)

        # 技术面条件 B：放量突破上轨 (今天突破，昨天在下，且今日成交量大于5日均量1.5倍)
        tech_breakout = (df['Close'] > bb_up) & (df['Close'].shift(1) <= bb_up.shift(1))
        tech_volume_surge = df['Volume'] > (vol_ma5.shift(1) * 1.5)

        # 基本面条件 C：净利润高增长 (兼容处理：如果df中没有这列，则默认跳过该检查)
        if 'net_profit_growth' in df.columns:
            fund_high_growth = df['net_profit_growth'] > 20.0
        else:
            # 在没有财务数据传入的回测环境中，退化为纯技术面的杯柄突破策略
            fund_high_growth = pd.Series(True, index=df.index)

            # 综合买入：大牛市背景 + 放量突破 + 业绩暴增
        buy_cond = tech_bull_market & tech_breakout & tech_volume_surge & fund_high_growth

        # --- 3. 组装卖出条件 (Sell) ---
        # 欧奈尔卖出法则：跌破 50 日均线 (机构护盘线被击穿) 止损/止盈
        sell_cond = df['Close'] < ma50

        # --- 4. 生成信号 ---
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1

        return df
    def test(self):
        """
        # 1. 拿到 K 线数据
        df_kline = get_kline_data("AAPL")  # 假设有 Date, Open, High, Low, Close, Volume

        # 2. 拿到季报财务数据
        df_finance = get_finance_data("AAPL")
        # 假设有 Report_Date(财报发布日), net_profit_growth

        # 3. 将财报数据按日期合并到 K 线上
        # 因为财报一个季度发一次，我们需要用 ffill (前向填充) 让每天的K线都能读到最新的财报数据
        df = pd.merge(df_kline, df_finance[['Report_Date', 'net_profit_growth']],
                      left_on='Date', right_on='Report_Date', how='left')

        df['net_profit_growth'] = df['net_profit_growth'].fillna(method='ffill')

        # 如果在第一份财报发布前有空值，填个0防报错
        df['net_profit_growth'] = df['net_profit_growth'].fillna(0)

        # 4. 送入策略进行回测或信号生成
        strategy = CANSLIMModelStrategy()
        result_df = strategy.generate_signals(df)

        # 查看信号
        print(result_df[result_df['Signal'] == 1])
        """
        return  None