import pandas as pd
import numpy as np
from ta.trend import CCIIndicator, SMAIndicator

from ..core.base_strategy import BaseTradingStrategy
from ta.momentum import RSIIndicator, StochasticOscillator
from ..core.kdj import tdx_k_d
from ta.volatility import BollingerBands


class ChannelPullbackStrategy(BaseTradingStrategy):
    """策略 5: 趋势回踩确认"""

    @property
    def name(self) -> str: return "05. 趋势回踩确认"

    # 22. 趋势回踩确认 (ChannelPullbackStrategy)
    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "在中长期均线（如60日线）稳步向上的背景下，股价回调触碰该均线但收盘价未能有效跌破。"

    @property
    def principle(self) -> str: return "价值引力支撑。向上的长期均线是趋势多头的心理防线，价格靠近防线时会吸引大量踏空的右侧资金进场托盘。"

    def get_start_idx(self) -> int: return 60

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ma60 = SMAIndicator(df['Close'], 60).sma_indicator()
        df['Signal'] = 0

        trend_up = ma60 > ma60.shift(10)
        pullback = (df['Low'] <= ma60) & (df['Close'] > ma60)

        buy_cond = trend_up & pullback
        sell_cond = df['Close'] < ma60.shift(1)
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

class SingleBullishHoldStrategy(BaseTradingStrategy):
    """策略 14: 单阳不破"""

    @property
    def name(self) -> str: return "14. 单阳不破"

    # 31. 单阳不破 (SingleBullishHoldStrategy)
    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "出现一根涨幅>5%的大阳线后，连续4-5日的调整K线，其最低价都没有跌穿大阳线的开盘价底线。"

    @property
    def principle(self) -> str: return "主力洗盘底线防守。大阳线是主力的建仓或拉升成本区，随后的缩量回调如果始终不破大阳底部，说明主力高度控盘且护盘意愿坚决，随时准备发起第二波上攻。"

    def get_start_idx(self) -> int: return 10

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        
        # 🚀 优化：防止开盘价为 0 的异常股
        big_yang = (df['Close'] - df['Open']) / df['Open'].replace(0, np.nan) > 0.05
        
        # 过去4天最低价大于5天前的开盘价
        hold_base = df['Low'].rolling(4).min() > df['Open'].shift(4)

        buy_cond = big_yang.shift(4) & hold_base & (df['Close'] > df['Open'])
        sell_cond = df['Close'] < df['Open'].shift(4)
        df.loc[buy_cond.fillna(False), 'Signal'] = 1
        df.loc[sell_cond.fillna(False), 'Signal'] = -1
        return df


class BollingerRSIReversionStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "布林带 + RSI 极限反转"

    @property
    def category(self) -> str: return "均值回归"

    @property
    def description(self) -> str: return "跌破布林带下轨，且同一时刻RSI指标低于30（处于严重超卖区）。"

    @property
    def principle(self) -> str: return "双重极端共振。空间突破置信下限，动能触及冰点极值，向布林中轨回归的确定性极高。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        bb = BollingerBands(df['Close'], window=20, window_dev=2.0)
        rsi = RSIIndicator(df['Close'], 14).rsi()

        buy_cond = (df['Close'] < bb.bollinger_lband()) & (rsi < 30)
        sell_cond = (df['Close'] > bb.bollinger_mavg())  # 回归中轨即止盈

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class BBRSIReversionStrategy(BaseTradingStrategy):
    """策略 15: 布林带 + RSI 均值回归"""

    @property
    def name(self) -> str: return "15. 布林带均值回归"

    # 32. 布林带均值回归 (BBRSIReversionStrategy)
    @property
    def category(self) -> str: return "均值回归"

    @property
    def description(self) -> str: return "股价跌穿布林带下轨，且同一时间RSI指标跌破30进入严重超卖区。"

    @property
    def principle(self) -> str: return "多重极值共振。空间上突破了95%置信区间（布林带），动能上陷入了极度冰点（RSI）。这种双重极端的错杀往往在随后几天会迎来报复性的修复反抽。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        bb = BollingerBands(df['Close'], window=20)
        rsi = RSIIndicator(df['Close'], 14).rsi()
        df['Signal'] = 0

        buy_cond = (df['Close'] < bb.bollinger_lband()) & (rsi < 30)
        sell_cond = (df['Close'] > bb.bollinger_hband()) | (rsi > 70)
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class RSIStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "RSI 强弱指标波段策略"

    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "RSI跌破30并重新站回30之上时买入；超过70并跌破时卖出。"

    @property
    def principle(self) -> str: return "相对强弱动能测算。顺应市场在过度狂热（超买）和过度悲观（超卖）之间的情绪摇摆拐点。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        rsi = RSIIndicator(df['Close'], 14).rsi()

        buy_cond = (rsi > 30) & (rsi.shift(1) <= 30)
        sell_cond = (rsi < 70) & (rsi.shift(1) >= 70)

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class StochasticSwingStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "随机震荡(KDJ)波段策略"

    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "KDJ指标的K线在20以下的超卖区，向上穿越D线形成金叉。"

    @property
    def principle(self) -> str: return "严格限制超卖区金叉，过滤高位主力骗线，专吃恐慌错杀后的那一波修复反弹利润。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        stoch = StochasticOscillator(df['High'], df['Low'], df['Close'], 9, 3)
        k, d = tdx_k_d(stoch)

        buy_cond = (k > d) & (k.shift(1) <= d.shift(1)) & (k.shift(1) < 20)
        sell_cond = (k < d) & (k.shift(1) >= d.shift(1)) & (k.shift(1) > 80)

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

class BIASPanicStrategy(BaseTradingStrategy):
    """策略 19: BIAS 极度恐慌"""

    @property
    def name(self) -> str: return "19. BIAS 极度恐慌"

    # 36. BIAS 极度恐慌 (BIASPanicStrategy)
    @property
    def category(self) -> str: return "均值回归"

    @property
    def description(self) -> str: return "24日乖离率（BIAS）达 -20% 以下，严重向下偏离中期均线。"

    @property
    def principle(self) -> str: return "价格弹性引力定律。像皮筋一样，当股价在短期内被暴力拉扯偏离其内生价值（24日均线）达到不可思议的20%时，引力作用会强制将其拉回。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ma24 = SMAIndicator(df['Close'], 24).sma_indicator()
        bias24 = (df['Close'] - ma24) / ma24 * 100
        df['Signal'] = 0

        buy_cond = bias24 < -20
        sell_cond = bias24 > 0
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class BBLowerSupportStrategy(BaseTradingStrategy):
    """策略 22: 布林下轨支撑"""

    @property
    def name(self) -> str: return "22. 布林下轨支撑"

    # 23. 布林下轨支撑 (BBLowerSupportStrategy)
    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "价格跌破布林带下轨后，当日迅速被拉起，收盘价站回下轨之上并收阳线。"

    @property
    def principle(self) -> str: return "波动率极限修复。在没有明确趋势的震荡市中，95%的价格会运行在布林带内。刺穿下轨是情绪宣泄的极值，拉回下轨说明非理性杀跌结束。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        bb = BollingerBands(df['Close'], window=20)
        low = bb.bollinger_lband()
        df['Signal'] = 0

        # 🚀 优化：防抖处理。只有昨天收在下轨之下（恐慌），今天收回下轨之上（翻转），才算买点！
        panic_yesterday = df['Close'].shift(1) < low.shift(1)
        reclaim_today = (df['Low'] < low) & (df['Close'] > low) & (df['Close'] > df['Open'])
        
        buy_cond = panic_yesterday & reclaim_today
        sell_cond = df['Close'] > bb.bollinger_hband()
        df.loc[buy_cond.fillna(False), 'Signal'] = 1
        df.loc[sell_cond.fillna(False), 'Signal'] = -1
        return df


# ==========================================
# 🥇 1. 拉里·康纳斯 (Larry Connors) - RSI(2) 极限回归策略
# ==========================================
class ConnorsRSI2Strategy(BaseTradingStrategy):
    """
    流派：华尔街量化高频/波段 (极限均值回归)
    胜率极高的短线策略。核心逻辑：在长期上升趋势中，寻找短期的极端恐慌超卖点。
    条件：1. 收盘价 > 200日均线 (大趋势向上)
          2. 2周期 RSI < 10 (极度超卖，部分激进基金设为 5)
          3. 收盘价上穿 5日均线时立刻止盈卖出 (绝不贪婪，只吃反抽)
    """

    @property
    def name(self) -> str: return "👑 康纳斯 RSI(2) 极限回归"

    # 7. 康纳斯 RSI(2) 极限回归 (ConnorsRSI2Strategy)
    @property
    def category(self) -> str: return "均值回归"

    @property
    def description(self) -> str: return "长期多头趋势下，2周期RSI跌破10极度超卖时买入，反弹至5日线卖出。"

    @property
    def principle(self) -> str: return "行为金融学过度反应理论。上升趋势中的突发利空会导致散户非理性恐慌抛售，形成错杀，带来极高胜率的短期均值修复。"

    def get_start_idx(self) -> int: return 200

    def horizon_tags(self) -> list[str]:
        return ["long"]

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # 大趋势过滤
        ma200 = SMAIndicator(df['Close'], 200).sma_indicator()
        # 极短线均线(用于止盈)
        ma5 = SMAIndicator(df['Close'], 5).sma_indicator()
        # 极短期 RSI (极其敏感)
        rsi2 = RSIIndicator(df['Close'], 2).rsi()

        df['Signal'] = 0

        # 买入：长线向好，且短线被极端错杀 (RSI2 < 10)
        buy_cond = (df['Close'] > ma200) & (rsi2 < 10)

        # 卖出：反弹触及或突破 5 日均线立刻止盈逃顶
        sell_cond = df['Close'] > ma5

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


"""这是华尔街 Stat-Arb（统计套利）量化基金的基础模型。
它不看传统的超买超卖，而是直接计算价格偏离均值的标准差倍数（Z-Score）。
当 Z-Score 跌破 -2.0 时，从统计学上讲它属于 2% 的极端小概率事件，此时入场抄底胜率惊人。
"""
class ZScoreMeanReversionStrategy(BaseTradingStrategy):
    """
    策略 31: Z-Score 统计均值回归模型 (量化基金标准模型)
    逻辑：当价格偏离其 20 日均线超过 2 个标准差时买入抄底，回归均值时卖出。
    """

    @property
    def name(self) -> str: return "📐 Z-Score 极端偏离抄底"

    # 8. Z-Score 极端偏离抄底 (ZScoreMeanReversionStrategy)
    @property
    def category(self) -> str: return "均值回归"

    @property
    def description(self) -> str: return "价格向下偏离20日均线超过 2 个标准差 (Z-Score < -2.0) 时买入。"

    @property
    def principle(self) -> str: return "正态分布统计学。偏离均值2个标准差是概率不足5%的极小概率事件，标的资产具有极其强烈的向均值引力回归的数学属性。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        window = 20
        # 计算 20 日均值和标准差
        rolling_mean = df['Close'].rolling(window=window).mean()
        rolling_std = df['Close'].rolling(window=window).std()

        # 计算 Z-Score: (当前价 - 均值) / 标准差
        z_score = (df['Close'] - rolling_mean) / rolling_std

        df['Signal'] = 0

        # 买入条件：Z-Score 小于 -2.0 (极端超卖区)，且今日 Z-Score 开始拐头向上 (防止接飞刀)
        buy_cond = (z_score < -2.0) & (z_score > z_score.shift(1))

        # 卖出条件：Z-Score 回归到 0 以上 (价格回到均线)
        sell_cond = z_score > 0

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

# ----------------- 【类别五：形态与波动率】 -----------------

class CCITurningStrategy(BaseTradingStrategy):
    """策略 20: CCI 弱转强"""

    @property
    def name(self) -> str: return "20. CCI 弱转强"

    # 37. CCI 弱转强 (CCITurningStrategy)
    @property
    def category(self) -> str: return "短线异动"

    @property
    def description(self) -> str: return "CCI顺势指标由下向上突破 -100 地平线（从极度超卖区回归正常区）。"

    @property
    def principle(self) -> str: return "异动回归。CCI专治‘不正常’。当价格脱离了统计学上的非正常下跌区域（<-100）重返人间时，意味着短线空头陷阱被识破，短线行情正式转强。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        cci = CCIIndicator(df['High'], df['Low'], df['Close'], 14).cci()
        df['Signal'] = 0

        buy_cond = (cci.shift(1) < -100) & (cci > -100)
        sell_cond = (cci.shift(1) > 100) & (cci < 100)
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

