import pandas as pd
from ..core.base_strategy import BaseTradingStrategy
from ta.trend import ADXIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ..core.kdj import tdx_k_d, tdx_k_d_j


class MACDBottomCrossStrategy(BaseTradingStrategy):
    """策略 8: MACD 水下金叉 (超跌企稳)"""

    @property
    def name(self) -> str: return "08. MACD 水下金叉"

    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "MACD的快慢线（DIF和DEA）在零轴下方发生黄金交叉。"

    @property
    def principle(self) -> str: return "动量加速度翻转。快线是对价格近期变动的敏感反应，快线上穿慢线代表近期的做多加速度已经超越了历史平均水平。"

    def get_start_idx(self) -> int: return 35

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        macd = MACD(df['Close'])
        dif, dea = macd.macd(), macd.macd_signal()
        df['Signal'] = 0

        buy_cond = (dif < 0) & (dea < 0) & (dif > dea) & (dif.shift(1) <= dea.shift(1))
        sell_cond = (dif < dea)
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class MACDDivergenceStrategy(BaseTradingStrategy):
    """策略 9: MACD 底背离"""

    @property
    def name(self) -> str: return "09. MACD 底背离"

    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "股价创出阶段新低，但MACD动能柱拒绝创出新低并拐头向上。"

    @property
    def principle(self) -> str: return "内在动能背离定律。表象（价格）在下跌，但本质（动能/买盘资金）却在不断增强，表象最终会向本质屈服回归。"

    def get_start_idx(self) -> int: return 40

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        macd = MACD(df['Close'])
        dif = macd.macd()
        macd_hist = macd.macd_diff()
        df['Signal'] = 0

        # 🚀 优化：确保严谨的价格新低和指标拒绝新低判定
        # 今天收盘价 <= 过去20天的最低价（注意使用 <= 防止平盘干扰）
        price_new_low = df['Close'] <= df['Close'].rolling(20).min().shift(1)

        # DIF 必须明确高于过去20天DIF的最低点
        dif_no_new_low = dif > dif.rolling(20).min().shift(1)

        # 动能柱拐点确认：今天比昨天强，且昨天是近3天最弱的（确认V型反转拐点）
        hist_turning_up = (macd_hist > macd_hist.shift(1)) & (macd_hist.shift(1) <= macd_hist.shift(2))

        buy_cond = price_new_low & dif_no_new_low & hist_turning_up
        sell_cond = macd.macd() < macd.macd_signal() # DIF 跌破 DEA 即死叉离场
        df.loc[buy_cond.fillna(False), 'Signal'] = 1
        df.loc[sell_cond.fillna(False), 'Signal'] = -1
        return df

class KDJGoldenPitStrategy(BaseTradingStrategy):
    """策略 17: KDJ 黄金坑 (J线战法)"""

    @property
    def name(self) -> str: return "17. KDJ 黄金坑"

    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "KDJ中极度敏锐的J线昨日跌破0轴进入负值泥潭，今日强力反抽至0轴上方。"

    @property
    def principle(self) -> str: return "微观情绪极寒反转。J线破零意味着短线抛压达到极不合理的变态程度，此时空头往往已无筹码可抛。一旦J线上穿零轴，多头微小的反击就能引发逼空式大涨。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        stoch = StochasticOscillator(df['High'], df['Low'], df['Close'], 9, 3)
        k, d, j = tdx_k_d_j(stoch)
        df['Signal'] = 0

        buy_cond = (j.shift(1) < 0) & (j > 0) & (k < 30)
        sell_cond = (j.shift(1) > 100) & (j < 100)
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class RSIReversalStrategy(BaseTradingStrategy):
    """策略 18: RSI 超卖拐点"""

    @property
    def name(self) -> str: return "18. RSI 超卖拐点"

    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "14日RSI跌破20进入极度冰点后，第二日动能衰竭，RSI数值拐头向上。"

    @property
    def principle(self) -> str: return "内在动能率先修复。价格可能因为惯性还在微跌，但其内部的下跌加速度（RSI）已经减缓，是典型的左侧捕捉见底信号的战法。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        rsi = RSIIndicator(df['Close'], 14).rsi()
        df['Signal'] = 0

        buy_cond = (rsi.shift(1) < 20) & (rsi > rsi.shift(1))
        sell_cond = rsi > 70
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

class TDXPrecisionStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "通达信精准买卖点"

    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "空方动能（-DI）极度衰竭反转，且KDJ在底部的共振金叉发出的复合买点。"

    @property
    def principle(self) -> str: return "游资合成因子战法。捕捉暴力洗盘后空头抛压耗尽的起涨拐点。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        adx_ind = ADXIndicator(df['High'], df['Low'], df['Close'], 14)
        _pdi, mdi = adx_ind.adx_pos(), adx_ind.adx_neg()
        stoch = StochasticOscillator(df['High'], df['Low'], df['Close'], 9, 3)
        k, d = tdx_k_d(stoch)

        mdi_exhaustion = (mdi < mdi.shift(1)) & (mdi.shift(1) > 25)
        kdj_cross = (k > d) & (k.shift(1) <= d.shift(1)) & (k.shift(1) < 30)

        buy_cond = mdi_exhaustion & kdj_cross
        sell_cond = (k < d) & (k.shift(1) >= d.shift(1)) & (k.shift(1) > 80)

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class Sperandeo2BReversalStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "维克多 2B 底部假跌破猎杀"

    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "近期跌破重要的前低支撑位，但迅速收出阳线并收复该支撑位。"

    @property
    def principle(self) -> str: return "流动性猎杀机制。主力砸破支撑触发散户止损盘吸筹，完毕后迅速拉升形成多头反扑。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        recent_low = df['Low'].rolling(20).min().shift(1)

        new_low_recently = (df['Low'].shift(1) <= recent_low.shift(1))
        reclaim_support = (df['Close'] > recent_low) & (df['Close'] > df['Open'])

        buy_cond = new_low_recently & reclaim_support
        sell_cond = df['Close'] < SMAIndicator(df['Close'], 10).sma_indicator()

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class TDSequentialSetupStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "⏱️ 汤姆·迪马克 TD9 衰竭反转"

    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "连续9天收盘价低于4天前的收盘价，且第9天收阳线反转。"

    @property
    def principle(self) -> str: return "单边动能衰竭定律。市场极少呈现无止境的单边下跌，连续9个周期的单向沉淀往往意味着空头力量被彻底耗尽。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        condition_buy = df['Close'] < df['Close'].shift(4)
        condition_sell = df['Close'] > df['Close'].shift(4)
        td_buy_9 = condition_buy.rolling(9).sum() == 9
        td_sell_9 = condition_sell.rolling(9).sum() == 9
        confirm_reversal = df['Close'] > df['Open']

        buy_cond = td_buy_9 & confirm_reversal
        sell_cond = td_sell_9

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class WyckoffSpringStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "📉 威科夫 弹簧效应与恐慌吸收"

    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "放巨量砸穿前期铁底，但收盘价收在全天振幅上半区（留长下影线）。"

    @property
    def principle(self) -> str: return "聪明钱吸收理论。巨量下跌是散户的恐慌抛售，而长下影线揭示了机构正在不计成本地接盘。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0
        recent_support = df['Low'].rolling(20).min().shift(1)
        vol_ma20 = SMAIndicator(df['Volume'], 20).sma_indicator()

        break_support = df['Low'] < recent_support
        panic_volume = df['Volume'] > (vol_ma20 * 2.0)
        smart_money_absorption = (df['Close'] - df['Low']) > ((df['High'] - df['Low']) * 0.5)

        buy_cond = break_support & panic_volume & smart_money_absorption
        sell_cond = df['Close'] > SMAIndicator(df['Close'], 20).sma_indicator()

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df
