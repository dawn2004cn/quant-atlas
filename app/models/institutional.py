import numpy as np
import pandas as pd
from ta.trend import MACD, ADXIndicator, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange
from ta.volume import ChaikinMoneyFlowIndicator, OnBalanceVolumeIndicator, VolumePriceTrendIndicator

from ..core.base_strategy import BaseTradingStrategy


class OBVAccumulationStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "OBV 底部吸筹 (主力潜伏)"

    @property
    def category(self) -> str: return "机构资金"

    @property
    def description(self) -> str: return "股价在一个极小的箱体内横盘，但能量潮指标（OBV）不断创出近期新高。"

    @property
    def principle(self) -> str: return "筹码暗中转移。下跌缩量，上涨放量。主力通过‘小阴线洗盘，大阳线吃货’收集筹码。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        obv = OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()

        # 优化：提取重复计算，提升性能
        roll_15_max = df['Close'].rolling(15).max()
        roll_15_min = df['Close'].rolling(15).min()

        # 优化：防止除以0
        price_flat = (roll_15_max - roll_15_min) / roll_15_min.replace(0, np.nan) < 0.05

        # OBV 创出 20 天新高
        obv_breakout = obv > obv.rolling(20).max().shift(1)

        buy_cond = price_flat & obv_breakout
        sell_cond = df['Close'] < roll_15_min.shift(1)

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ==========================================
# ⚖️ 10. 量价趋势背离 (VPT Institutional Divergence)
# ==========================================
class VPTDivergenceStrategy(BaseTradingStrategy):
    """
    流派：量价微观结构 (机构建仓雷达)
    逻辑：OBV 的升级版。VPT (量价趋势指标) 将成交量与价格涨跌幅的百分比相结合。
    底背离：股价在创出近期新低（跌势看似惨烈），但 VPT 指标却拒绝创出新低。
    这说明下跌时的阴线都是无量空跌（散户踩踏），而上涨时的阳线都是放量（主力暗中吃货）。
    """

    @property
    def name(self) -> str: return "⚖️ 机构 VPT 量价底背离"

    # 12. MACD 底背离 / VPT 量价底背离
    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "股价创出阶段新低，但MACD动能柱/VPT量价指标拒绝创出新低并拐头向上。"

    @property
    def principle(self) -> str: return "内在动能背离定律。表象（价格）在下跌，但本质（动能/买盘资金）却在不断增强，表象最终会向本质屈服回归。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0

        # 计算 VPT (ta 库自带)
        vpt = VolumePriceTrendIndicator(df['Close'], df['Volume']).volume_price_trend()

        # 价格创 20 日新低
        price_new_low = df['Close'] < df['Close'].rolling(20).min().shift(1)

        # VPT 拒绝创 20 日新低 (形成抬高的底部)
        vpt_no_new_low = vpt > vpt.rolling(20).min().shift(1)

        # 动能确认：当天收实体阳线(>2%)，且成交量大于昨日
        bull_candle = (df['Close'] - df['Open']) / df['Open'].replace(0, np.nan) > 0.02
        vol_up = df['Volume'] > df['Volume'].shift(1)

        buy_cond = price_new_low & vpt_no_new_low & bull_candle & vol_up

        # 卖出：VPT 死叉其 10 日均线
        vpt_ma10 = SMAIndicator(vpt, 10).sma_indicator()
        sell_cond = vpt < vpt_ma10

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df



class StrongTrendDipStrategy(BaseTradingStrategy):
    """策略 24: 强势股首阴/回调"""

    @property
    def name(self) -> str: return "24. 强势股首阴回调"

    # 14. 强势股首阴 / 缩量回踩 (StrongTrendDipStrategy)
    @property
    def category(self) -> str: return "动量回调"

    @property
    def description(self) -> str: return "前期涨幅巨大的强势股，首次收阴跌至 10 日线附近。"

    @property
    def principle(self) -> str: return "游资龙头战法。极强势股的第一次大跌往往是主力洗盘或前期获利盘涌出，跌至短期支撑位会引发强烈的资金自救和二波博弈预期。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ma10 = SMAIndicator(df['Close'], 10).sma_indicator()
        ma20 = SMAIndicator(df['Close'], 20).sma_indicator()
        df['Signal'] = 0

        strong_past = ma10 > ma20 * 1.05
        # 优化：加上 shift(1) 条件，确保是“首次”回踩，而不是一直在均线上蹭
        first_dip = (df['Low'].shift(1) > ma10.shift(1)) & (df['Low'] <= ma10) & (df['Close'] > ma10)

        buy_cond = strong_past & first_dip
        sell_cond = df['Close'] < ma20
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ==========================================
# 🏆 2. 马克·米勒维尼 (Mark Minervini) - VCP 波动率收缩突破
# ==========================================
class MinerviniVCPStrategy(BaseTradingStrategy):
    """
    流派：全美投资大赛冠军 (动量成长股)
    华尔街最著名的成长股战法：VCP (Volatility Contraction Pattern)。
    核心逻辑：股票在爆发前，会在右侧形成波动率和成交量的双重收缩（洗盘），随后放量突破。
    条件：符合“趋势模板”（价格在52周高点附近，MA50>MA150>MA200），且近期缩量后突然放量突破。
    """

    @property
    def name(self) -> str: return "🏆 米勒维尼 VCP 波动率收缩突破"

    # 1. 米勒维尼 VCP 波动率收缩突破 (MinerviniVCPStrategy)
    @property
    def category(self) -> str: return "动量成长"

    @property
    def description(self) -> str: return "价格处于200日线上方，近期成交量极度萎缩，随后放量突破前期高点。"

    @property
    def principle(self) -> str: return "微观筹码理论。成交量萎缩代表浮筹清洗完毕（供给枯竭），此时主力只需微小的资金点火，就能引发巨大的向上突破爆发。"

    def get_start_idx(self) -> int: return 250  # 需要计算 52 周 (250个交易日) 的高低点

    def horizon_tags(self) -> list[str]:
        return ["long"]

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ma50 = SMAIndicator(df['Close'], 50).sma_indicator()
        ma150 = SMAIndicator(df['Close'], 150).sma_indicator()
        ma200 = SMAIndicator(df['Close'], 200).sma_indicator()
        vol_ma50 = SMAIndicator(df['Volume'], 50).sma_indicator()

        # 计算 52 周 (约250天) 最高点和最低点
        high_52w = df['High'].rolling(250).max()
        low_52w = df['Low'].rolling(250).min()

        df['Signal'] = 0

        # 1. 趋势模板 (Trend Template) 严格过滤
        trend_template = (
                (df['Close'] > ma50) & (ma50 > ma150) & (ma150 > ma200) &
                (ma200 > ma200.shift(20)) &  # 200日线必须至少向上倾斜
                (df['Close'] > low_52w * 1.3) &  # 价格比52周低点高出30%以上
                (df['Close'] > high_52w * 0.75)  # 价格距离52周高点不到25%
        )

        # 2. VCP 洗盘特征：过去5天极度缩量 (成交量远低于50日均量)，代表浮筹清洗完毕
        volume_contraction = df['Volume'].rolling(5).max().shift(1) < vol_ma50.shift(1)

        # 3. 突破特征：今天突破近20日新高，且放出巨量
        price_breakout = df['Close'] > df['High'].rolling(20).max().shift(1)
        volume_surge = df['Volume'] > vol_ma50 * 1.5

        buy_cond = trend_template & volume_contraction & price_breakout & volume_surge

        # 卖出：跌破 50 日线 (机构生命线) 坚决止损
        sell_cond = df['Close'] < ma50

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class RaschkeHolyGrailStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "琳达·拉什克 圣杯回调"

    @property
    def category(self) -> str: return "机构资金"  # 或动量回调

    @property
    def description(self) -> str: return "ADX>30的强劲单边趋势中，价格首次回调并精准踩中 20 日均线。"

    @property
    def principle(self) -> str: return "强趋势不会轻易终结，首次回调到中期生命线必然会遇到庞大的机构顺势买盘托底。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        adx = ADXIndicator(df['High'], df['Low'], df['Close'], 14).adx()
        ema20 = EMAIndicator(df['Close'], 20).ema_indicator()

        strong_trend = (adx > 30) & (adx > adx.shift(1))
        # 优化：确保是回踩动作
        pullback = (df['Low'].shift(1) > ema20.shift(1)) & (df['Low'] <= ema20) & (df['Close'] > ema20)

        buy_cond = strong_trend.shift(1) & pullback
        sell_cond = df['Close'] < ema20

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

# ==========================================
# 🩺 4. 亚历山大·埃尔德 (Alexander Elder) - 脉冲交易系统
# ==========================================
class ElderImpulseStrategy(BaseTradingStrategy):
    """
    流派：华尔街著名交易心理大师 (多周期动量过滤)
    逻辑：结合了 13 日 EMA（顺势）和 MACD 柱状图（动量）。
    当 EMA 和 MACD 柱子同时向上时，市场处于“绿色脉冲”（绝对禁止做空，强烈做多）。
    当两者同时向下时，处于“红色脉冲”（绝对禁止做多，清仓）。
    """

    @property
    def name(self) -> str: return "🩺 埃尔德 脉冲交易系统"

    # 17. 埃尔德 脉冲交易系统 (ElderImpulseStrategy)
    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "13日EMA均线向上，且MACD柱状图同时向上（绿色脉冲）。"

    @property
    def principle(self) -> str: return "动量与趋势多周期共振。均线代表群体价值共识的方向，MACD柱代表群体情绪的加速度，两者同向时波段爆发力最强。"

    def get_start_idx(self) -> int: return 35

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ema13 = EMAIndicator(df['Close'], 13).ema_indicator()
        macd = MACD(df['Close'])
        macd_hist = macd.macd_diff()

        df['Signal'] = 0

        # 均线向上发散
        ema_rising = ema13 > ema13.shift(1)
        # 动能柱向上生长
        hist_rising = macd_hist > macd_hist.shift(1)

        ema_falling = ema13 < ema13.shift(1)
        hist_falling = macd_hist < macd_hist.shift(1)

        # 绿色脉冲：双龙出海，果断买入
        buy_cond = ema_rising & hist_rising & (df['Close'] > ema13)

        # 红色脉冲：动能和趋势同时衰竭，清仓
        sell_cond = ema_falling & hist_falling

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

class VWAPPullbackStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "🏢 机构 VWAP 锚定回踩"

    # 15. 机构 VWAP 锚定回踩 (VWAPPullbackStrategy)
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "当价格向上突破锚定VWAP后，首次回踩该线时买入。"

    @property
    def principle(self) -> str: return "VWAP是机构算法交易(TWAP/VWAP)的平均成本线。跌到此线机构有动力护盘填单。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        # 计算 20 日滚动 VWAP (简化版锚定 VWAP)
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vol_price = typical_price * df['Volume']

        # 优化：防止成交量为0导致的除零异常
        vol_sum = df['Volume'].rolling(20).sum()
        rolling_vwap = vol_price.rolling(20).sum() / vol_sum.replace(0, np.nan)

        # 强趋势过滤：VWAP 必须在上升
        vwap_rising = rolling_vwap > rolling_vwap.shift(1)
        # 回踩动作：最低价触碰或跌破VWAP，但收盘价站稳之上
        pullback = (df['Low'].shift(1) > rolling_vwap.shift(1)) & (df['Low']  <= rolling_vwap) & (df['Close'] > rolling_vwap)

        buy_cond = vwap_rising & pullback
        sell_cond = df['Close'] < rolling_vwap  # 有效跌破机构成本线

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

class ChaikinMoneyFlowStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "💸 蔡金资金流 (CMF) 主力潜伏"

    # 16. 蔡金资金流 主力潜伏 (ChaikinMoneyFlowStrategy)
    @property
    def category(self) -> str: return "机构资金"

    @property
    def description(self) -> str: return "股价不断创新低，但 CMF 指标稳步上升翻红。"

    @property
    def principle(self) -> str: return "CMF结合了收盘价在日内振幅中的位置与成交量。底背离说明下跌是散户砸盘，而主力在日内悄悄吸收筹码并将收盘价托起。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        cmf = ChaikinMoneyFlowIndicator(df['High'], df['Low'], df['Close'], df['Volume'],
                                        window=20).chaikin_money_flow()

        # 股价创 20 日新低
        price_new_low = df['Close'] < df['Close'].rolling(20).min().shift(1)
        # 优化：不仅要大于0，而且要比昨天高（动能向上）
        money_flowing_in = (cmf > 0) & (cmf > cmf.shift(1))

        buy_cond = price_new_low & money_flowing_in
        sell_cond = cmf < -0.1  # 资金转为大幅流出

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

class ChoppinessIndexStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "🌀 Choppiness Index 混沌突破"

    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "当 CHOP 指数极高（市场极度混乱震荡）后，突然回落配合价格突破。"

    @property
    def principle(self) -> str: return "基于分形几何理论。CHOP>61.8表示市场处于无序的随机漫步。当其跌破61.8说明混沌结束，一波大级别的确定性趋势已经降临。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        n = 14
        tr = AverageTrueRange(df['High'], df['Low'], df['Close'], 1).average_true_range()
        atr_sum = tr.rolling(n).sum()

        high_max = df['High'].rolling(n).max()
        low_min = df['Low'].rolling(n).min()

        # 优化：极其关键的除零保护！如果股价长达14天不动（一字板），high_max - low_min 会等于0
        price_range = (high_max - low_min).replace(0, np.nan)

        # 计算 CHOP 指数
        chop = 100 * np.log10(atr_sum / price_range) / np.log10(n)

        # 昨天还在极度混沌 (CHOP > 61.8)，今天混沌解除 (CHOP < 61.8) 且价格创 14 天新高
        chaos_ends = (chop.shift(1) > 61.8) & (chop < 61.8)
        breakout = df['Close'] > df['High'].rolling(14).max().shift(1)

        buy_cond = chaos_ends & breakout
        sell_cond = chop > 61.8  # 重新陷入混沌，平仓离场

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

