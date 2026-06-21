import numpy as np
import pandas as pd
import yfinance as yf
from abc import ABC, abstractmethod

# 导入 TA 库指标
from ta.trend import SMAIndicator, EMAIndicator, MACD, CCIIndicator, IchimokuIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange, KeltnerChannel, DonchianChannel
from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator, VolumePriceTrendIndicator
from ta.trend import EMAIndicator, ADXIndicator
from ta.momentum import StochasticOscillator
import warnings

warnings.filterwarnings('ignore')


# ==========================================
# 1. 抽象策略接口 (Strategy Interface)
# ==========================================
class BaseTradingStrategy(ABC):
    """
    交易策略抽象基类。
    所有具体的交易策略都必须继承该类并实现 generate_signals 方法。
    """

    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def category(self) -> str:
        """策略分类：趋势突破 / 均值回归 / 震荡波段 / 恐慌抄底 / 机构资金"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """给交易员看的策略简述"""
        pass

    @property
    @abstractmethod
    def principle(self) -> str:
        """底层金融学与行为学原理"""
        pass
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        根据历史数据生成买卖信号
        :param df: 包含 Open, High, Low, Close, Volume 的 DataFrame
        :return: 带有 'Signal' 列的 DataFrame (1: 买入, -1: 卖出, 0: 观望)
        """
        pass

    @abstractmethod
    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        pass
# ==========================================
# 2. 具体策略实现 (Concrete Strategies)
# ==========================================

class MAStrategy(BaseTradingStrategy):
    """MA策略"""
    @property
    def name(self) -> str:
        return "1: MA策略"

    # ==========================================
    # 5. MA 双均线交叉策略 (MAStrategy / DualMovingAverageStrategy)
    # ==========================================
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "短周期移动平均线（如5日或20日）向上穿越长周期移动平均线（如20日或60日），形成‘黄金交叉’。"

    @property
    def principle(
            self) -> str: return "最古老也最坚韧的趋势跟踪法则。均线代表参与者的平均成本。短期均线上穿长期均线，说明近期入场的资金不仅愿意以更高的价格买入，并且已经成功解放了长线套牢盘，市场正式由空头主导转为多头主导。"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        运行MA策略，生成交易信号

        Args:
            data: 股票历史数据

        Returns:
            pd.DataFrame: 带有交易信号的数据
        """
        # 使用 ta 库计算MA指标
        data['MA5'] = SMAIndicator(close=data['Close'], window=5).sma_indicator()
        data['MA20'] = SMAIndicator(close=data['Close'], window=20).sma_indicator()

        # 生成交易信号
        data['Signal'] = 0
        data.loc[data['MA5'] > data['MA20'], 'Signal'] = 1
        data.loc[data['MA5'] < data['MA20'], 'Signal'] = -1

        return data

    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        return 20


class RSIStrategy(BaseTradingStrategy):
    """RSI策略"""

    @property
    def name(self) -> str:
        return "2:  RSI策略"

    # ==========================================
    # 6. RSI 强弱指标策略 (RSIStrategy)
    # ==========================================
    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "通常在 RSI 跌破 30 并重新站回 30 之上时买入；在 RSI 超过 70 并重新跌破 70 时卖出平仓。"

    @property
    def principle(
            self) -> str: return "相对强弱动能测算。RSI 衡量的是上涨力量与下跌力量的拔河比赛。它认为行情总是在过度狂热（超买）和过度悲观（超卖）之间摇摆。顺应这种情绪摇摆的拐点，就能吃到最肥美的波段鱼身。"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        运行RSI策略，生成交易信号

        Args:
            data: 股票历史数据

        Returns:
            pd.DataFrame: 带有交易信号的数据
        """
        # 使用 ta 库计算RSI指标
        data['RSI'] = RSIIndicator(close=data['Close'], window=14).rsi()

        # 生成交易信号
        data['Signal'] = 0
        data.loc[data['RSI'] < 30, 'Signal'] = 1  # 超卖买入
        data.loc[data['RSI'] > 70, 'Signal'] = -1  # 超买卖出

        return data

    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        return 14


class TAUStrategy(BaseTradingStrategy):
    """TAU策略"""
    @property
    def name(self) -> str:
        return "3:  TAU策略"

    # ==========================================
    # 7. TAU策略 (TAUStrategy - 假设为动量/周期混合测算策略)
    # ==========================================
    # 注：TAU 通常在量化中指代时间周期系数或特定的希腊字母衍生模型（例如基于半衰期的动量衰减）。这里我以通用的 TAU 时序动量模型为你编写：
    @property
    def category(self) -> str: return "动量成长"

    @property
    def description(
            self) -> str: return "基于时间加权收益率的动量策略（Time-Weighted Average Upside）。它给予近期收益更高的权重，当短期加权上涨动能突破长期历史阈值时买入。"

    @property
    def principle(
            self) -> str: return "动量时间衰减理论。金融市场具有记忆性，但记忆会随时间指数级衰减。近期发生的放量大涨对未来趋势的影响，远大于半年前的涨停。TAU 捕捉的就是这种‘刚刚爆发、记忆犹新’的最强动能。"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        运行TAU策略，生成交易信号

        Args:
            data: 股票历史数据

        Returns:
            pd.DataFrame: 带有交易信号的数据
        """
        # 1. 计算趋势强度指标
        # MA 趋势
        data['MA20'] = SMAIndicator(close=data['Close'], window=20).sma_indicator()
        data['MA20_5'] = data['MA20'].shift(5)

        # MACD 指标
        macd = MACD(close=data['Close'])
        data['MACD'] = macd.macd()
        data['Signal'] = macd.macd_signal()
        data['MACD_Hist'] = macd.macd_diff()

        # RSI 指标
        data['RSI'] = RSIIndicator(close=data['Close'], window=14).rsi()
        data['RSI_5'] = data['RSI'].shift(5)

        # 价格形态
        data['Recent_High'] = data['High'].rolling(window=10).max()
        data['Recent_Low'] = data['Low'].rolling(window=20).min()

        # 2. 计算市场活跃度指标
        # 成交量
        data['Volume_MA5'] = data['Volume'].rolling(window=5).mean()
        data['Volume_Ratio'] = data['Volume'] / (data['Volume_MA5'] + 1e-9)

        # 波动幅度
        data['Daily_Change'] = data['Close'].pct_change().abs()
        data['Volatility'] = data['Daily_Change'].rolling(window=5).mean()

        # 3. 综合评分
        data['Trend_Score'] = 0
        # 价格位于20日均线上方
        data.loc[data['Close'] > data['MA20'], 'Trend_Score'] += 10
        # 20日均线向上
        data.loc[data['MA20'] > data['MA20_5'], 'Trend_Score'] += 10
        # MACD 金叉
        data.loc[data['MACD'] > data['Signal'], 'Trend_Score'] += 5
        # 柱状图由负转正
        data.loc[data['MACD_Hist'] > 0, 'Trend_Score'] += 5
        # RSI 在50以上
        data.loc[data['RSI'] > 50, 'Trend_Score'] += 5
        # RSI 呈现上升趋势
        data.loc[data['RSI'] > data['RSI_5'], 'Trend_Score'] += 5
        # 价格突破近期高点
        data.loc[data['Close'] >= data['Recent_High'], 'Trend_Score'] += 5
        # 形成上升通道
        data.loc[data['Low'] > data['Recent_Low'], 'Trend_Score'] += 5

        data['Activity_Score'] = 0
        # 成交量放大
        data.loc[data['Volume_Ratio'] > 1.5, 'Activity_Score'] += 10
        data.loc[(data['Volume_Ratio'] > 1) & (data['Volume_Ratio'] <= 1.5), 'Activity_Score'] += 5
        # 波动适中
        data.loc[(data['Volatility'] >= 0.01) & (data['Volatility'] <= 0.05), 'Activity_Score'] += 5

        # 综合评分
        data['Total_Score'] = data['Trend_Score'] + data['Activity_Score']

        # 4. 生成交易信号
        data['Signal'] = 0
        # 评分高于45分买入
        data.loc[data['Total_Score'] > 45, 'Signal'] = 1
        # 评分低于30分卖出
        data.loc[data['Total_Score'] < 30, 'Signal'] = -1

        return data

    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        return 26  # 需要足够的历史数据计算指标

class BollingerRSIReversionStrategy(BaseTradingStrategy):
    """策略 2: 布林带 + RSI 极限反转策略 (均值回归)"""

    @property
    def name(self) -> str:
        return "4:  布林带 + RSI 极限反转策略 (均值回归)"

    # ==========================================
    # 1. 布林带 + RSI 极限反转策略 (BollingerRSIReversionStrategy)
    # ==========================================
    @property
    def category(self) -> str: return "均值回归"

    @property
    def description(self) -> str: return "股价跌破布林带下轨，且同一时刻RSI指标低于30（处于严重超卖区）。"

    @property
    def principle(
            self) -> str: return "双重极端共振。布林带下轨代表了价格在统计概率上突破了 95% 的置信区间下限；RSI < 30 代表了动能上的极度恐慌。当空间和动能同时触及冰点极值时，向均值（布林中轨）回归的确定性极高。"
    def __init__(self, bb_window=20, rsi_window=14):
        self.bb_window = bb_window
        self.rsi_window = rsi_window

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # 计算指标
        bb = BollingerBands(close=df['Close'], window=self.bb_window, window_dev=2)
        df['BB_low'] = bb.bollinger_lband()
        df['BB_high'] = bb.bollinger_hband()
        df['RSI'] = RSIIndicator(close=df['Close'], window=self.rsi_window).rsi()

        df['Signal'] = 0
        # 跌破下轨且极端超卖 -> 买入
        buy_cond = (df['Close'] < df['BB_low']) & (df['RSI'] < 30)
        # 突破上轨且极端超买 -> 卖出
        sell_cond = (df['Close'] > df['BB_high']) & (df['RSI'] > 70)

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        return 20

class EMAMACDContinuationStrategy(BaseTradingStrategy):
    """策略 3: EMA长线顺势 + MACD回调策略 (动量顺势)"""

    @property
    def name(self) -> str:
        return "5: EMA长线顺势 + MACD回调策略 (动量顺势)"

    # 25. EMA顺势 MACD回调 (EMAMACDContinuationStrategy)
    @property
    def category(self) -> str: return "动量回调"

    @property
    def description(self) -> str: return "价格运行在120日均线上方的大牛市中，MACD短线经历死叉回调后，再次在零轴上方或附近金叉。"

    @property
    def principle(self) -> str: return "顺大势逆小势。在长线保护下，利用MACD捕捉短线获利盘回吐结束的节点，是兼具高胜率和高盈亏比的右侧战法。"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # 计算指标
        df['EMA_200'] = EMAIndicator(close=df['Close'], window=200).ema_indicator()
        macd = MACD(close=df['Close'])
        df['MACD_line'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()

        df['Signal'] = 0
        # MACD 金叉 & 死叉 判定
        macd_golden = (df['MACD_line'] > df['MACD_signal']) & (df['MACD_line'].shift(1) <= df['MACD_signal'].shift(1))
        macd_death = (df['MACD_line'] < df['MACD_signal']) & (df['MACD_line'].shift(1) >= df['MACD_signal'].shift(1))

        # 大趋势向上且短期金叉 -> 买入
        buy_cond = (df['Close'] > df['EMA_200']) & macd_golden
        # 死叉 -> 卖出
        sell_cond = macd_death

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        return 200

class VolumeBreakoutStrategy(BaseTradingStrategy):
    """策略 4: 底部放量突破策略 (量价配合)"""

    @property
    def name(self) -> str:
        return "6: 底部放量突破策略 (量价配合)"

    # ==========================================
    # 2. 底部放量突破策略 (VolumeBreakoutStrategy)
    # ==========================================
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "股价长期在低位横盘后，突然放出一根历史级别的巨量（远超近期均量），并强力向上突破盘整区或重要阻力位（如布林带上轨）。"

    @property
    def principle(
            self) -> str: return "量在价先。底部长期横盘意味着散户被深套死扛，没有任何交易意愿。此时的‘底部爆量’绝对不是散户所为，而是机构/游资不计成本大口吞吃带血筹码的抢筹行为，是主升浪开启的冲锋号。"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # 计算指标
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BB_high'] = bb.bollinger_hband()
        df['BB_mid'] = bb.bollinger_mavg()

        df['OBV'] = OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume']).on_balance_volume()
        df['OBV_SMA'] = SMAIndicator(close=df['OBV'], window=20).sma_indicator()

        df['Signal'] = 0
        # 突破上轨且 OBV 在均线上方 (买盘强劲) -> 买入
        buy_cond = (df['Close'] > df['BB_high']) & (df['OBV'] > df['OBV_SMA'])
        # 跌破中轨 (均线) -> 卖出
        sell_cond = (df['Close'] < df['BB_mid'])

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        return 20

class StochasticSwingStrategy(BaseTradingStrategy):
    """策略 5: 随机震荡(KDJ)波段策略 (震荡市波段)"""

    @property
    def name(self) -> str:
        return "7: 随机震荡(KDJ)波段策略 (震荡市波段)"

    # ==========================================
    # 3. 随机震荡(KDJ)波段策略 (StochasticSwingStrategy)
    # ==========================================
    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "在震荡市或上升通道的回调期，KDJ指标的K线在20以下的超卖区，向上穿越D线形成金叉买入。"

    @property
    def principle(self) -> str: return "波段动能翻转。KDJ对微小的价格反转极其敏感。通过严格限制‘只能在20以下的超卖区金叉’，过滤掉了中高位主力骗线的假金叉，专吃恐慌错杀后的那一波修复反弹利润。"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # 计算指标
        stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3)
        df['Stoch_K'] = stoch.stoch_signal()
        df['Stoch_D'] = stoch.stoch()
        df['SMA_50'] = SMAIndicator(close=df['Close'], window=50).sma_indicator()

        df['Signal'] = 0
        # K线上穿D线(金叉) 且处于超卖区(<20) 且 大趋势(SMA50)向上
        buy_cond = (
                (df['Stoch_K'] > df['Stoch_D']) & (df['Stoch_K'].shift(1) <= df['Stoch_D'].shift(1)) &
                (df['Stoch_K'] < 20) &
                (df['Close'] > df['SMA_50'])
        )

        # K线下穿D线(死叉) 且处于超买区(>80)
        sell_cond = (
                (df['Stoch_K'] < df['Stoch_D']) & (df['Stoch_K'].shift(1) >= df['Stoch_D'].shift(1)) &
                (df['Stoch_K'] > 80)
        )

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df

    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        return 50

class TDXPrecisionStrategy(BaseTradingStrategy):
    """
    通达信《精准买卖点》转化策略 (去除未来函数版)
    利用原脚本中的 EMA均线束、DMI(趋向指标) 以及 KDJ 底部特征来捕捉买卖点。
    """
    @property
    def name(self) -> str:
        return "8: 通达信精准买卖点策略 (去除未来函数版)"

    # ==========================================
    # 4. 通达信精准买卖点策略 (TDXPrecisionStrategy)
    # ==========================================
    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "结合了多周期均线束发散程度、DMI(趋向指标)的极度背离，以及KDJ在底部的共振金叉发出的复合买点信号。"

    @property
    def principle(
            self) -> str: return "A股流传甚广的游资合成因子战法。它剥离了原版中带有‘未来函数’的画线部分，保留了‘当空方动能（-DI）极度衰竭，且随机震荡（KDJ）出现底背离反抽时入场’的科学内核，擅长捕捉暴力洗盘后的起涨拐点。"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # ----------------------------------------------------
        # 1. 还原源码中的均线系统 (MA5 到 MA250)
        # 原码: MA5:=EMA(CLOSE,5); MA10:=EMA...
        # ----------------------------------------------------
        ema_periods = [5, 10, 20, 28, 48, 120, 250]
        for period in ema_periods:
            df[f'EMA_{period}'] = EMAIndicator(close=df['Close'], window=period).ema_indicator()

        # ----------------------------------------------------
        # 2. 还原源码中的 VAR1 - VAR7 (实际上是 DMI 指标的 +DI 和 -DI)
        # 原码 VAR6 是 +DI，VAR7 是 -DI。ta 库原生支持，无需手动循环算SUM。
        # ----------------------------------------------------
        adx_indicator = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=25)
        df['VAR6_PDI'] = adx_indicator.adx_pos()  # 对应源码的 VAR6
        df['VAR7_MDI'] = adx_indicator.adx_neg()  # 对应源码的 VAR7

        # 还原源码中 A 的逻辑：A:=(VAR7>VAR6 AND VAR7>25 AND VAR6<25); (代表处于明显下跌趋势)
        df['Cond_A'] = (df['VAR7_MDI'] > df['VAR6_PDI']) & (df['VAR7_MDI'] > 25) & (df['VAR6_PDI'] < 25)

        # ----------------------------------------------------
        # 3. 还原源码中的 VAR11 - VAR14 (实际上是 KDJ 随机震荡指标)
        # 原码 VAR11 是 RSV，VAR12 是 K，VAR13 是 D
        # ----------------------------------------------------
        stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=9, smooth_window=3)
        df['VAR12_K'] = stoch.stoch_signal()  # 通达信 K
        df['VAR13_D'] = stoch.stoch()  # 通达信 D

        # 还原源码中 VAR14 逻辑: VAR13 AND VAR13<20 (D线在超卖区)
        df['VAR14'] = df['VAR13_D'] < 20

        # ----------------------------------------------------
        # 4. 生成因果买卖信号 (替代 ZIG 的偷看未来)
        # ----------------------------------------------------
        df['Signal'] = 0

        # 捕捉反转(金叉/死叉)逻辑
        cross_up = (df['VAR12_K'] > df['VAR13_D']) & (df['VAR12_K'].shift(1) <= df['VAR13_D'].shift(1))
        cross_down = (df['VAR12_K'] < df['VAR13_D']) & (df['VAR12_K'].shift(1) >= df['VAR13_D'].shift(1))

        # 🎯 买入信号 (对应源码的 ↖买，但不使用未来函数)
        # 逻辑：当 KDJ 在底部形成金叉 (捕捉波谷)，并且短期跌幅够深(利用VAR14)，或者短期均线抬头
        buy_condition = cross_up & df['VAR14']

        # 🎯 卖出信号 (对应源码的 逃)
        # 逻辑：当 KDJ 在高位(如 D>80) 发生死叉，逃顶。
        sell_condition = cross_down & (df['VAR13_D'] > 80)

        # 为了对应源码中的 FILTER(D=1, 5) (过滤掉过于密集的信号，这里做一个简单的 Pandas 阻断)
        # Pandas 向量化处理过滤稍复杂，我们这里采用“状态位”或直接记录信号
        # 这里简化处理：直接采用条件判断
        df.loc[buy_condition, 'Signal'] = 1
        df.loc[sell_condition, 'Signal'] = -1

        return df

    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        return 50



# ==========================================
# 📈 2. 策略子类大全 (25 种核心战法)
# ==========================================

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

        max_ma = pd.concat([ma10, ma20, ma60], axis=1).max(axis=1)
        min_ma = pd.concat([ma10, ma20, ma60], axis=1).min(axis=1)

        df['Signal'] = 0
        squeeze = (max_ma - min_ma) / min_ma < 0.02
        buy_cond = squeeze.shift(1) & (df['Close'] > max_ma) & (df['Close'] > df['Open'])
        sell_cond = df['Close'] < ma20

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


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


# ----------------- 【类别二：MACD与动能】 -----------------

class EMAMACDContinuationStrategy(BaseTradingStrategy):
    """策略 6: EMA顺势 MACD 回调"""

    @property
    def name(self) -> str: return "06. EMA顺势MACD回调"

    def get_start_idx(self) -> int: return 120

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
    def category(self) -> str: return "动量成长" / "恐慌抄底"

    @property
    def description(self) -> str: return "MACD的快慢线（DIF和DEA）在零轴上方（或下方）发生黄金交叉。"

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


class MACDBottomCrossStrategy(BaseTradingStrategy):
    """策略 8: MACD 水下金叉 (超跌企稳)"""

    @property
    def name(self) -> str: return "08. MACD 水下金叉"

    # 26. MACD 水上金叉 (MACDZeroCrossStrategy) / MACD 水下金叉 (MACDBottomCrossStrategy)
    @property
    def category(self) -> str: return "动量成长" / "恐慌抄底"

    @property
    def description(self) -> str: return "MACD的快慢线（DIF和DEA）在零轴上方（或下方）发生黄金交叉。"

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
    def description(self) -> str: return "股价创出阶段新低，但MACD动能柱/VPT量价指标拒绝创出新低并拐头向上。"

    @property
    def principle(self) -> str: return "内在动能背离定律。表象（价格）在下跌，但本质（动能/买盘资金）却在不断增强，表象最终会向本质屈服回归。"

    def get_start_idx(self) -> int: return 40

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        macd = MACD(df['Close'])
        dif, macd_hist = macd.macd(), macd.macd_diff()
        df['Signal'] = 0

        price_new_low = df['Close'] < df['Close'].rolling(20).min().shift(1)
        dif_no_new_low = dif > dif.rolling(20).min().shift(1)
        hist_turning_up = macd_hist > macd_hist.shift(1)

        buy_cond = price_new_low & dif_no_new_low & hist_turning_up
        sell_cond = macd.macd() < macd.macd_signal()
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


class OBVAccumulationStrategy(BaseTradingStrategy):
    """策略 12: OBV 底部吸筹"""

    @property
    def name(self) -> str: return "12. OBV 底部吸筹"

    # 29. OBV 底部吸筹 (OBVAccumulationStrategy)
    @property
    def category(self) -> str: return "机构资金"

    @property
    def description(self) -> str: return "股价在一个极小的箱体内横盘长达数周，但能量潮指标（OBV）却不断创出近期新高。"

    @property
    def principle(self) -> str: return "筹码暗中转移。下跌缩量，上涨放量。主力在横盘区通过‘小阴线洗盘，大阳线吃货’的方式收集筹码，导致股价不涨但累计资金净流入暴增。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        obv = OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
        df['Signal'] = 0

        price_consolidation = (df['Close'].rolling(10).max() - df['Close'].rolling(10).min()) / df['Close'].rolling(
            10).min() < 0.05
        obv_breakout = obv >= obv.rolling(20).max().shift(1)

        buy_cond = price_consolidation & obv_breakout
        sell_cond = df['Close'] < df['Close'].rolling(10).min().shift(1)
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
        big_yang = (df['Close'] - df['Open']) / df['Open'] > 0.05
        # 过去4天最低价大于5天前的开盘价
        hold_base = df['Low'].rolling(4).min() > df['Open'].shift(4)

        buy_cond = big_yang.shift(4) & hold_base & (df['Close'] > df['Open'])
        sell_cond = df['Close'] < df['Open'].shift(4)
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ----------------- 【类别四：震荡与超跌】 -----------------

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


class KDJSwingStrategy(BaseTradingStrategy):
    """策略 16: KDJ 波段超卖金叉"""

    @property
    def name(self) -> str: return "16. KDJ 波段金叉"

    # 33. KDJ 波段金叉 (KDJSwingStrategy)
    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "KDJ指标的K值在30以下的超卖区，向上穿越D值形成黄金交叉。"

    @property
    def principle(self) -> str: return "震荡市短线转折。过滤掉中高位的无效交叉，只在短线情绪最绝望的底部捕捉买盘资金入场带来的短波段反弹利润。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        stoch = StochasticOscillator(df['High'], df['Low'], df['Close'], 9, 3)
        k, d = stoch.stoch_signal(), stoch.stoch()
        df['Signal'] = 0

        buy_cond = (k > d) & (k.shift(1) <= d.shift(1)) & (k.shift(1) < 30)
        sell_cond = (k < d) & (k.shift(1) >= d.shift(1)) & (k.shift(1) > 70)
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class KDJGoldenPitStrategy(BaseTradingStrategy):
    """策略 17: KDJ 黄金坑 (J线战法)"""

    @property
    def name(self) -> str: return "17. KDJ 黄金坑"

    # 34. KDJ 黄金坑 (KDJGoldenPitStrategy)
    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "KDJ中极度敏锐的J线昨日跌破0轴进入负值泥潭，今日强力反抽至0轴上方。"

    @property
    def principle(self) -> str: return "微观情绪极寒反转。J线破零意味着短线抛压达到极不合理的变态程度，此时空头往往已无筹码可抛。一旦J线上穿零轴，多头微小的反击就能引发逼空式大涨。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        stoch = StochasticOscillator(df['High'], df['Low'], df['Close'], 9, 3)
        k, d = stoch.stoch_signal(), stoch.stoch()
        j = 3 * k - 2 * d
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

    # 35. RSI 超卖拐点 (RSIReversalStrategy)
    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "14日RSI跌破20进入极度冰点后，第二日动能衰竭，RSI数值拐头向上。"

    @property
    def principle(self) -> str: return "内在动能率先修复。价格可能因为惯性还在微跌，但其内部的下跌加速度（RSI）已经减缓，是典型的左侧左半部分捕捉见底信号的战法。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        rsi = RSIIndicator(df['Close'], 14).rsi()
        df['Signal'] = 0

        buy_cond = (rsi.shift(1) < 20) & (rsi > rsi.shift(1))
        sell_cond = rsi > 70
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

        buy_cond = (df['Low'] < low) & (df['Close'] > low) & (df['Close'] > df['Open'])
        sell_cond = df['Close'] > bb.bollinger_hband()
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
        dip_support = (df['Low'] <= ma10) & (df['Close'] > ma10)

        buy_cond = strong_past & dip_support
        sell_cond = df['Close'] < ma20
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
    def name(self) -> str: return "27.🌟 TTM Squeeze 挤压爆发模型"

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
    def name(self) -> str: return "28.🐉 顾比复合均线 (GMMA) 共振"

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
    def name(self) -> str: return "29.☁️ 一目均衡表 (云层突破)"

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
    def name(self) -> str: return "30.📐 Z-Score 极端偏离抄底"

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


"""
大师级策略的实战底层逻辑解析：
康纳斯 RSI(2) (机构级统计回归)：不要小看这简单的几行代码。
散户喜欢用 14 日 RSI，但康纳斯通过百万次计算机回测发现，在长期多头趋势（>MA200）中，遇到突发利空导致 RSI(2) < 10 时，随后的 1-3 天内向上反弹的概率高达 80% 以上。这就是量化高频波段吃肉的无情机器。

米勒维尼 VCP (超级大牛股模板)：
你在 A 股或美股看到的那些 1 个月翻倍的妖股，起涨前 90% 都符合 VCP 形态。代码里的 volume_contraction（成交量萎缩到50日均量以下）是精髓：这意味着里面被套牢的人已经彻底绝望不再卖出（浮筹清洗完毕），一旦 volume_surge 机构稍微用点资金点火，股价就会毫无阻力地一飞冲天。

琳达·拉什克 圣杯 (顺势者的信仰)：
ADX 是所有趋势指标之王。当 ADX > 30 时，说明一辆高铁正在全速前进。此时你不敢追高，那么等它第一次减速（回踩 20 日 EMA均线）时，就是唯一的上车机会。

维克多 2B 法则 (流动性猎杀/Smart Money)：
这个模型体现了“反散户人性”。主力资金（Smart Money）体量太大，想建仓必须制造恐慌。他们会故意把股价砸破重要的前期支撑位，触发散户的自动止损单（爆出巨大流动性），主力顺势接盘后迅速拉升（收复失地）。如果你抓住了 reclaim_support，你就是跟庄吃肉。
"""

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
    def name(self) -> str: return "31.👑 康纳斯 RSI(2) 极限回归"

    # 7. 康纳斯 RSI(2) 极限回归 (ConnorsRSI2Strategy)
    @property
    def category(self) -> str: return "均值回归"

    @property
    def description(self) -> str: return "长期多头趋势下，2周期RSI跌破10极度超卖时买入，反弹至5日线卖出。"

    @property
    def principle(self) -> str: return "行为金融学过度反应理论。上升趋势中的突发利空会导致散户非理性恐慌抛售，形成错杀，带来极高胜率的短期均值修复。"

    def get_start_idx(self) -> int: return 200

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
    def name(self) -> str: return "32.🏆 米勒维尼 VCP 波动率收缩突破"

    # 1. 米勒维尼 VCP 波动率收缩突破 (MinerviniVCPStrategy)
    @property
    def category(self) -> str: return "动量成长"

    @property
    def description(self) -> str: return "价格处于200日线上方，近期成交量极度萎缩，随后放量突破前期高点。"

    @property
    def principle(self) -> str: return "微观筹码理论。成交量萎缩代表浮筹清洗完毕（供给枯竭），此时主力只需微小的资金点火，就能引发巨大的向上突破爆发。"

    def get_start_idx(self) -> int: return 250  # 需要计算 52 周 (250个交易日) 的高低点

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


# ==========================================
# 🧙‍♀️ 3. 琳达·拉什克 (Linda Raschke) - 圣杯回撤策略 (Holy Grail)
# ==========================================
class RaschkeHolyGrailStrategy(BaseTradingStrategy):
    """
    流派：华尔街顶级女交易员 (经典动量回撤)
    逻辑：在极强的单边趋势中（ADX>30），等价格第一次回调触碰 20日 EMA 时上车。
    这就是趋势交易里的“千金难买牛回头”。
    """

    @property
    def name(self) -> str: return "33.🧙‍♀️ 琳达·拉什克 圣杯回调法则"

    # 13. 琳达·拉什克 圣杯回调 (RaschkeHolyGrailStrategy)
    @property
    def category(self) -> str: return "动量回调"

    @property
    def description(self) -> str: return "ADX>30的强劲单边趋势中，价格首次回调并精准踩中 20 日均线。"

    @property
    def principle(self) -> str: return "趋势均值回归。强趋势不会轻易终结，首次回调到中期生命线必然会遇到庞大的顺势买盘（踏空资金补仓）托底。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        adx_ind = ADXIndicator(df['High'], df['Low'], df['Close'], 14)
        adx = adx_ind.adx()
        ema20 = EMAIndicator(df['Close'], 20).ema_indicator()

        df['Signal'] = 0

        # 条件 1：强趋势确立 (ADX > 30 且 ADX 还在上升)
        strong_trend = (adx > 30) & (adx > adx.shift(1))

        # 条件 2：价格精准回踩 EMA20 (最低价跌破或碰到均线，但收盘价站稳均线之上)
        # 用 shift(1) 确保昨天或今天是回调的，且趋势仍然在
        pullback = (df['Low'] <= ema20) & (df['Close'] > ema20)

        buy_cond = strong_trend.shift(1) & pullback

        # 卖出：收盘价跌破 EMA20 且无法收回，说明趋势破坏
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
    def name(self) -> str: return "34.🩺 埃尔德 脉冲交易系统"

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


# ==========================================
# 🦅 5. 维克多·斯波朗迪 (Trader Vic) - 2B 假突破反转法则
# ==========================================
class Sperandeo2BReversalStrategy(BaseTradingStrategy):
    """
    流派：华尔街传奇交易员 (裸K形态学 / 流动性猎杀)
    逻辑：华尔街机构专门用来绞杀散户突破盘的“2B法则”。
    当价格突破前高（散户疯狂追涨），但在随后的 3 天内迅速跌破该前高（多头陷阱）。
    此时反向做空或清仓逃顶，或者在底部发生假跌破时重仓抄底。
    这里实现的是【底部 2B 假跌破抄底做多】模型。
    """

    @property
    def name(self) -> str: return "35.🦅 维克多 2B 底部假跌破猎杀"

    # 9. 维克多 2B 假跌破猎杀 (Sperandeo2BReversalStrategy)
    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "近期跌破重要的前低支撑位，但随后几个交易日内迅速收出阳线并收复该支撑位。"

    @property
    def principle(self) -> str: return "流动性猎杀机制 (Stop Run)。主力故意砸破支撑触发大量散户的止损盘（获取流动性吃货），吸筹完毕后迅速拉升，形成多头反扑。"

    def get_start_idx(self) -> int: return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # 获取过去 20 天的最低点 (近期支撑位)
        recent_low = df['Low'].rolling(20).min().shift(1)

        df['Signal'] = 0

        # 1. 昨天或前天创出新低 (跌破支撑，散户恐慌抛售/止损盘被触发)
        new_low_recently = (df['Low'].shift(1) <= recent_low.shift(1)) | (df['Low'].shift(2) <= recent_low.shift(2))

        # 2. 今天不仅没有继续大跌，收盘价反而强势收复了那个“被跌破的支撑位” (机构吃完带血筹码后拉升)
        # 并且收一根阳线
        reclaim_support = (df['Close'] > recent_low) & (df['Close'] > df['Open'])

        buy_cond = new_low_recently & reclaim_support

        # 卖出：价格再次跌破今天的最低价（说明抄底失败，真破位了），严格止损
        # 在向量化中，我们简单用跌破 10日线 作为波段止盈损点
        sell_cond = df['Close'] < SMAIndicator(df['Close'], 10).sma_indicator()

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ==========================================
# ⏱️ 6. 汤姆·迪马克 (Tom DeMark) - TD序列 极限反转
# ==========================================
class TDSequentialSetupStrategy(BaseTradingStrategy):
    """
    流派：华尔街顶级神算子 (左侧摸底/逃顶天花板)
    逻辑：华尔街各大投行终端机（如彭博社）标配的昂贵指标。
    当连续 9 天的收盘价，都低于其各自 4 天前的收盘价时，被称为“TD买入结构 9”。
    这在统计学上代表着“下跌动能已经彻底衰竭到极限”，即将发生大级别反转。
    """

    @property
    def name(self) -> str: return "36.⏱️ 汤姆·迪马克 TD9 衰竭反转"

    # 10. TD9 衰竭反转 (TDSequentialSetupStrategy)
    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "连续9天收盘价低于4天前的收盘价，且第9天收阳线反转。"

    @property
    def principle(self) -> str: return "单边动能衰竭定律。市场极少呈现无止境的单边下跌，连续9个周期的单向沉淀往往意味着空头力量被彻底耗尽，面临报复性反转。"

    def get_start_idx(self) -> int: return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0

        # 核心逻辑：今日收盘 < 4天前的收盘
        condition_buy = df['Close'] < df['Close'].shift(4)
        condition_sell = df['Close'] > df['Close'].shift(4)

        # 连续 9 天满足上述条件 (极其罕见且有效)
        td_buy_9 = condition_buy.rolling(9).sum() == 9
        td_sell_9 = condition_sell.rolling(9).sum() == 9

        # 过滤接飞刀：第 9 天必须收一根阳线或长下影线才买入 (确认主力接盘)
        confirm_reversal = df['Close'] > df['Open']

        buy_cond = td_buy_9 & confirm_reversal
        sell_cond = td_sell_9

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ==========================================
# 📉 7. 威科夫操盘法 (Richard Wyckoff) - 弹簧效应与恐慌抛售
# ==========================================
class WyckoffSpringStrategy(BaseTradingStrategy):
    """
    流派：百年经典量价分析祖师爷 (聪明钱 Smart Money 追踪)
    逻辑：威科夫理论的灵魂在于“测试底部的弹簧效应 (Spring)”。
    主力在拉升前，会故意砸破前期的铁底支撑位，引发散户的恐慌抛售（爆出巨量）。
    但聪明钱会把筹码全部吃掉，导致当天收盘价被强力拉回中高位（留下长下影的爆量K线）。
    """

    @property
    def name(self) -> str: return "37.📉 威科夫 弹簧效应与恐慌吸收"

    # 11. 威科夫弹簧效应 (WyckoffSpringStrategy)
    @property
    def category(self) -> str: return "恐慌抄底"

    @property
    def description(self) -> str: return "放巨量砸穿前期铁底，但收盘价收在全天振幅上半区（留长下影线）。"

    @property
    def principle(self) -> str: return "聪明钱 (Smart Money) 吸收理论。巨量下跌是散户的恐慌抛售，而长下影线揭示了机构正在不计成本地接下这些带血筹码。"

    def get_start_idx(self) -> int: return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0

        # 过去 20 天的最低价（散户眼里的铁底）
        recent_support = df['Low'].rolling(20).min().shift(1)
        vol_ma20 = SMAIndicator(df['Volume'], 20).sma_indicator()

        # 1. 跌破铁底，制造恐慌
        break_support = df['Low'] < recent_support

        # 2. 爆出巨量 (成交量大于 20日均量的 2 倍)，散户绝望交出带血筹码
        panic_volume = df['Volume'] > (vol_ma20 * 2.0)

        # 3. 聪明钱吸收：收盘价不但没有死在最低点，反而收在了全天振幅的上半区 (长下影线)
        # (Close - Low) / (High - Low) > 0.5
        smart_money_absorption = (df['Close'] - df['Low']) > ((df['High'] - df['Low']) * 0.5)

        buy_cond = break_support & panic_volume & smart_money_absorption

        # 卖出：反弹至 20日均线压力位止盈
        sell_cond = df['Close'] > SMAIndicator(df['Close'], 20).sma_indicator()

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


# ==========================================
# 🎯 8. 托比·克拉贝尔 (Toby Crabel) - NR7 波动率极小值爆发
# ==========================================
class NR7BreakoutStrategy(BaseTradingStrategy):
    """
    流派：华尔街自营盘暴利秘籍 (窄幅震荡突破)
    逻辑：这是量化短线客最爱的日内/隔日战法。NR7 代表“过去 7 天内振幅最小的一天”。
    金融市场是呼吸的，波动率收缩到了极致（NR7），明天大概率发生剧烈的单边爆发。
    此时只要挂单突破 NR7 的最高点，瞬间就能吃大肉。
    """

    @property
    def name(self) -> str: return "38.🎯 托比·克拉贝尔 NR7 极致窄幅爆发"

    # 18. NR7 极致窄幅爆发 (NR7BreakoutStrategy)
    @property
    def category(self) -> str: return "趋势突破"

    @property
    def description(self) -> str: return "昨日振幅是过去7天内最小的(NR7)，今日价格突破昨日最高点。"

    @property
    def principle(self) -> str: return "微观波动率收缩极值。金融市场的波动率呈周期性脉冲，极致的死寂（NR7）必然酝酿着多空平衡的瞬间打破和单边行情的井喷。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Signal'] = 0

        # 计算每天的真实振幅
        daily_range = df['High'] - df['Low']

        # 寻找 NR7 (今天的振幅是过去 7 天里最小的)
        is_nr7 = daily_range == daily_range.rolling(7).min()

        # 爆发买点：昨天是 NR7 极致压缩，今天价格突破昨天最高点
        buy_cond = is_nr7.shift(1) & (df['Close'] > df['High'].shift(1))

        # 爆发做空/平仓：昨天是 NR7，今天跌破昨天最低点
        sell_cond = is_nr7.shift(1) & (df['Close'] < df['Low'].shift(1))

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
    def name(self) -> str: return "39.🐊 比尔·威廉姆斯 鳄鱼苏醒"

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
        max_line = pd.concat([jaw, teeth, lips], axis=1).max(axis=1)
        min_line = pd.concat([jaw, teeth, lips], axis=1).min(axis=1)
        sleeping = ((max_line - min_line) / min_line) < 0.015

        # 鳄鱼张嘴 (苏醒做多)：唇线 > 齿线 > 颚线，且昨天还在睡觉
        awakening = (lips > teeth) & (teeth > jaw)
        buy_cond = sleeping.shift(1) & awakening

        # 鳄鱼闭嘴 (吃饱离场)：唇线向下跌破齿线
        sell_cond = lips < teeth

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
    def name(self) -> str: return "40.⚖️ 机构 VPT 量价底背离"

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

        # 动能确认：当天收长阳线，且成交量大于昨日
        bull_candle = (df['Close'] - df['Open']) / df['Open'] > 0.02
        vol_up = df['Volume'] > df['Volume'].shift(1)

        buy_cond = price_new_low & vpt_no_new_low & bull_candle & vol_up

        # 卖出：VPT 死叉其 10 日均线
        vpt_ma10 = SMAIndicator(vpt, 10).sma_indicator()
        sell_cond = vpt < vpt_ma10

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class ChoppinessIndexStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "41.🌀 Choppiness Index 混沌突破"

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
        atr_sum = AverageTrueRange(df['High'], df['Low'], df['Close'], 1).average_true_range().rolling(n).sum()
        high_max = df['High'].rolling(n).max()
        low_min = df['Low'].rolling(n).min()

        # 计算 CHOP 指数
        chop = 100 * np.log10(atr_sum / (high_max - low_min)) / np.log10(n)

        # 昨天还在极度混沌 (CHOP > 61.8)，今天混沌解除 (CHOP < 61.8) 且价格创 14 天新高
        chaos_ends = (chop.shift(1) > 61.8) & (chop < 61.8)
        breakout = df['Close'] > df['High'].rolling(14).max().shift(1)

        buy_cond = chaos_ends & breakout
        sell_cond = chop > 61.8  # 重新陷入混沌，平仓离场

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
    def name(self) -> str: return "42.🏮 吊灯止损空翻多突破"

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


class VWAPPullbackStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "43.🏢 机构 VWAP 锚定回踩"

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
        rolling_vwap = vol_price.rolling(20).sum() / df['Volume'].rolling(20).sum()

        # 强趋势过滤：VWAP 必须在上升
        vwap_rising = rolling_vwap > rolling_vwap.shift(1)
        # 回踩动作：最低价触碰或跌破VWAP，但收盘价站稳之上
        pullback = (df['Low'] <= rolling_vwap) & (df['Close'] > rolling_vwap)

        buy_cond = vwap_rising & pullback
        sell_cond = df['Close'] < rolling_vwap  # 有效跌破机构成本线

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class ChaikinMoneyFlowStrategy(BaseTradingStrategy):
    @property
    def name(self) -> str: return "44.💸 蔡金资金流 (CMF) 主力潜伏"

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
        # CMF 大于 0 (资金净流入状态)
        money_flowing_in = cmf > 0

        buy_cond = price_new_low & money_flowing_in
        sell_cond = cmf < -0.1  # 资金转为大幅流出

        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df


class MarketRegimeManager:
    """大盘环境风控官 (Regime Filter)"""

    def __init__(self, index_df: pd.DataFrame):
        """
        传入大盘指数数据 (如上证指数、标普500)
        """
        self.index_df = index_df
        # 预先计算大盘的状态
        self.ma50 = SMAIndicator(index_df['Close'], 50).sma_indicator()
        self.ma200 = SMAIndicator(index_df['Close'], 200).sma_indicator()

    def get_regime(self, date) -> str:
        """获取某一天的大盘状态：牛市、熊市、震荡市"""
        try:
            # 获取当天的指数数据
            c = self.index_df.loc[date, 'Close']
            m50 = self.ma50.loc[date]
            m200 = self.ma200.loc[date]

            if pd.isna(m200): return "震荡市"  # 数据不足默认震荡

            if c > m200 and m50 > m200:
                return "牛市"  # 强趋势多头
            elif c < m200 and m50 < m200:
                return "熊市"  # 强趋势空头
            else:
                return "震荡市"  # 上下穿越无明确方向
        except:
            return "震荡市"

"""
终极指引：如何在代码中使用这些元数据？
一旦你的策略装配了这些属性，你在 HolyGrailEnsembleEngine 里的打分输出就可以变得像专业机构的研究报告一样震撼。

例如，在发现买点时，你可以让系统这样输出：

[系统检测到极高置信度共振]
标的：贵州茅台 (600519)
大盘环境：【熊市下跌期】

触发模型 1：[恐慌抄底] 维克多 2B 假跌破猎杀
📌 盘面特征：近期跌破重要的前低支撑位，但随后几个交易日内迅速收出阳线并收复该支撑位。
🧠 机构揭秘：流动性猎杀机制。主力故意砸破支撑触发大量散户的止损盘获取流动性，吸筹完毕后迅速拉升。

触发模型 2：[恐慌抄底] MACD 底背离
📌 盘面特征：股价创出阶段新低，但MACD动能柱拒绝创出新低并拐头向上。
🧠 机构揭秘：内在动能背离定律。表象（价格）在下跌，但本质（买盘资金）却在不断增强。

这种不仅知其然（技术面形态），更知其所以然（主力资金逻辑）的系统，才是真正能让人有信心在实盘中按下买入键的超级量化机器。
"""
""""
一、 牛市专属激活：【趋势突破】与【动量成长】
# 1. 米勒维尼 VCP 波动率收缩突破 (MinerviniVCPStrategy)
# 2. TTM Squeeze 挤压爆发模型 (TTMSqueezeBreakoutStrategy)
# 3. 海龟交易法则 (TurtleTradingStrategy)
# 4. CANSLIM 戴维斯双击 (CANSLIMModelStrategy)
# 5. 一目均衡表云层突破 (IchimokuCloudStrategy)
# 6. 出水芙蓉 / 放量打拐 / 均线粘合突破 (VWAPPullbackStrategy)
二、熊市专属激活：【恐慌抄底】与【均值回归】
# 7. 康纳斯 RSI(2) 极限回归 (ConnorsRSI2Strategy)
# 8. Z-Score 极端偏离抄底 (ZScoreMeanReversionStrategy)
# 9. 维克多 2B 假跌破猎杀 (Sperandeo2BReversalStrategy)
# 10. TD9 衰竭反转 (TDSequentialSetupStrategy)
# 11. 威科夫弹簧效应 (WyckoffSpringStrategy)
# 12. MACD 底背离 / VPT 量价底背离
三、 顺势牛市/震荡反弹通用：【动量回调】与【机构资金】
# 13. 琳达·拉什克 圣杯回调 (RaschkeHolyGrailStrategy)
# 14. 强势股首阴 / 缩量回踩 (StrongTrendDipStrategy)
# 15. 机构 VWAP 锚定回踩 (VWAPPullbackStrategy)
# 16. 蔡金资金流 主力潜伏 (ChaikinMoneyFlowStrategy)
# 17. 埃尔德 脉冲交易系统 (ElderImpulseStrategy)
# 18. NR7 极致窄幅爆发 (NR7BreakoutStrategy)
四、 经典均线与通道战法：【趋势突破】与【震荡波段】
# 19. 双均线交叉策略 (DualMovingAverageStrategy)
# 20.经典多头排列 (MultiMAResonanceStrategy)
# 21. 均线粘合突破 (MASqueezeBreakoutStrategy)
# 22. 趋势回踩确认 (ChannelPullbackStrategy)
# 23. 布林下轨支撑 (BBLowerSupportStrategy)
# 24. 布林带缩口突破 (BBSqueezeStrategy)
五、 经典动量与异动战法：【动量成长】与【短线异动】
# 25. EMA顺势 MACD回调 (EMAMACDContinuationStrategy)
# 26. MACD 水上金叉 (MACDZeroCrossStrategy) / MACD 水下金叉 (MACDBottomCrossStrategy)
# 27. DMI 主升浪 (DMITrendStrategy)
# 28. 放量突破生命线 (VolMABreakoutStrategy)
# 29. OBV 底部吸筹 (OBVAccumulationStrategy)
# 30. 红三兵 (ThreeWhiteSoldiersStrategy)
# 31. 单阳不破 (SingleBullishHoldStrategy)
六、 极限震荡与异类形态：【均值回归】与【异动猎杀】
# 32. 布林带均值回归 (BBRSIReversionStrategy)
# 33. KDJ 波段金叉 (KDJSwingStrategy)
# 34. KDJ 黄金坑 (KDJGoldenPitStrategy)
# 35. RSI 超卖拐点 (RSIReversalStrategy)
# 36. BIAS 极度恐慌 (BIASPanicStrategy)
# 37. CCI 弱转强 (CCITurningStrategy)
# 38. ATR 波动扩张 (ATRExpansionStrategy)
# 39. 吊灯止损空翻多突破 (ChandelierExitStrategy)
# 40. 鳄鱼苏醒 (AlligatorAwakeningStrategy)
"""
class HolyGrailEnsembleEngine:
    """
    机构核心密码：带大盘过滤的投票机引擎
    """

    def __init__(self, index_df: pd.DataFrame):
        self.regime_manager = MarketRegimeManager(index_df)
        self.strategies: list[BaseTradingStrategy] = []

        # --- 策略库初始化 (把我们写的几十个策略全装进来) ---
        self.strategies.append(VWAPPullbackStrategy())
        self.strategies.append(ChaikinMoneyFlowStrategy())
        self.strategies.append(ChoppinessIndexStrategy())
        # self.strategies.append(ConnorsRSI2Strategy()) # 从上文引入
        # self.strategies.append(MinerviniVCPStrategy()) # 从上文引入
        # ... 凑齐 40 种甚至 100 种 ...

    def _get_active_categories(self, regime: str) -> list:
        """核心路由逻辑：不同环境，激活不同的武器库"""
        if regime == "牛市":
            # 牛市：做主升浪，敢于追高，寻找主力资金
            return ["趋势突破", "机构资金", "动量成长"]
        elif regime == "熊市":
            # 熊市：绝对禁止追高！只能做极限超跌和恐慌反弹
            return ["恐慌抄底", "均值回归", "2B假跌破"]
        else:  # 震荡市
            # 震荡市：高抛低吸，布林带最管用
            return ["均值回归", "震荡波段", "机构资金"]

    def run_scan(self, target_df: pd.DataFrame, target_name: str):
        """执行扫盘并汇总打分"""
        today = target_df.index[-1]

        # 1. 查询今天的大盘环境
        current_regime = self.regime_manager.get_regime(today)
        active_cats = self._get_active_categories(current_regime)

        print(f"\n📊 当前大盘环境: 【{current_regime}】")
        print(f"✅ 系统自动激活策略组: {active_cats}")
        print(f"🔍 正在扫描个股: {target_name} ...")

        buy_votes = 0
        triggered_models = []

        # 2. 遍历武器库
        for strategy in self.strategies:
            # 过滤1：如果该策略不适合当前大盘环境，直接禁用！(防坑核心)
            if strategy.category not in active_cats:
                continue

            # 过滤2：数据长度不够
            if len(target_df) < strategy.get_start_idx():
                continue

            # 生成信号
            sig_df = strategy.generate_signals(target_df.copy())

            # 如果今天该策略发出买入信号
            if sig_df['Signal'].iloc[-1] == 1:
                buy_votes += 1
                triggered_models.append({
                    "战法名称": strategy.name,
                    "流派": strategy.category,
                    "策略研报": strategy.description
                })

        # 3. 汇总投票结果
        total_active_strats = len([s for s in self.strategies if s.category in active_cats])
        if total_active_strats == 0: return

        # 算出共振得分 (满分 100)
        confidence_score = int((buy_votes / total_active_strats) * 100)

        if buy_votes > 0:
            print(f"\n🔥 发现买点！综合共振置信度: {confidence_score}分 (共 {buy_votes} 个顶级模型同时触发)")
            for m in triggered_models:
                print(f"  👉 [{m['流派']}] {m['战法名称']}")
                print(f"     💡 逻辑: {m['策略研报']}")
        else:
            print("💤 未触发买入信号。")
"""
进阶指导：为什么凑齐 100 种策略并不意味着无敌？
我们现在已经构建了接近 40 种涵盖各种流派的量化模型。如果你想继续挖到 100 种，无非是引入均值回归的各种变体（如 RSI+布林带，KDJ+均线）、机器学习衍生因子、各种稀奇古怪的 K 线组合（黄昏之星、三只乌鸦）。

但在华尔街的顶级量化工厂中，核心秘密在于 Model Ensemble（模型集成）与 Factor Rotation（因子轮动）：

熊市/震荡市期间：你应该只开启 ConnorsRSI2Strategy（极限短线抄底）、WyckoffSpringStrategy（恐慌抛售猎杀）。此时如果开启趋势突破模型，你会被来回打脸。

牛市初期：开启 TDSequentialSetupStrategy（TD9摸大底）、VPTDivergenceStrategy（量价背离建仓）。

牛市主升浪期间：重仓开启 MinerviniVCPStrategy（成长股VCP突破）、RaschkeHolyGrailStrategy（圣杯回调上车）。
"""
# ==========================================
# 3. 上下文管理 (Context) - 负责调用策略
# ==========================================
class TradingBot:
    """
    交易机器人(上下文)，用于管理和动态切换当前的交易策略。
    """

    def __init__(self, strategy: BaseTradingStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: BaseTradingStrategy):
        """动态更换策略"""
        print(f"🔄 正在切换策略至: {strategy.__class__.__name__}")
        self._strategy = strategy

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行当前绑定的策略"""
        # 使用 copy() 防止 pandas 的 SettingWithCopyWarning
        return self._strategy.generate_signals(df.copy())


# ==========================================
# 4. 执行入口 (Main)
# ==========================================
if __name__ == "__main__":
    # 1. 下载测试数据
    ticker = "AAPL"
    print(f"📥 正在下载 {ticker} 数据...")
    # 获取近两年的数据
    data = yf.download(ticker, start="2022-01-01", end="2024-01-01", progress=False)

    # yfinance最新版本返回可能包含多级列索引，先清理一下
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel('Ticker')

    # 2. 实例化所有可用策略
    strategies = {
        "1. 双均线策略": DualMovingAverageStrategy(short_window=20, long_window=60),
        "2. 布林带+RSI抄底": BollingerRSIReversionStrategy(),
        "3. MACD顺势回调": EMAMACDContinuationStrategy(),
        "4. 放量突破策略": VolumeBreakoutStrategy(),
        "5. KDJ波段策略": StochasticSwingStrategy(),
        "6. TDX精准买卖点策略": TDXPrecisionStrategy()
    }

    # 3. 初始化上下文 (先使用第一个策略)
    bot = TradingBot(list(strategies.values())[0])

    # 4. 遍历运行所有策略，查看信号输出
    for name, strategy_obj in strategies.items():
        print(f"\n{'=' * 50}")
        # 动态改变交易系统的策略
        bot.set_strategy(strategy_obj)

        # 获取含有信号的 DataFrame
        result_df = bot.run(data)

        # 统计产生买入和卖出信号的天数
        buy_signals = result_df[result_df['Signal'] == 1]
        sell_signals = result_df[result_df['Signal'] == -1]

        print(f"📊 策略 [{name}] 执行结果: ")
        print(f"   👉 共找到买入信号 (Buy):  {len(buy_signals)} 次")
        print(f"   👉 共找到卖出信号 (Sell): {len(sell_signals)} 次")

        # 打印最后一次买入信号的数据片段
        if not buy_signals.empty:
            print(f"   📅 最后一次买入发生日期: {buy_signals.index[-1].strftime('%Y-%m-%d')}")
            # 打印当时的收盘价
            print(f"   💰 当日收盘价: {buy_signals.iloc[-1]['Close']:.2f}")

        """
        为什么这是量化的最终答案？
        在普通的开源代码里，你只能看到一大堆指标的罗列。而上面的代码，展示了一个基金经理的真实大脑运作过程：

        宏观定调（Regime Filter）：大盘在暴跌（熊市）时，所有告诉你“均线金叉、向上突破”的模型都会被程序无情地锁死。资金被强行路由到“RSI极限超卖”或“跌破铁底恐慌吸收”这些反身性策略上。这保住了你的本金。

        多因子共振（Ensemble Voting）：单个策略的胜率即使高达 60%，也容易被单日游资骗线。但如果在一只股票上，分形理论的 Choppiness 说它混沌结束了，资金流的 CMF 说机构在潜伏，量价的 VWAP 说它回踩了成本线。当这三个毫不相干的数学模型在同一天同时发出 1 时，这就是胜率极高的“圣杯买点”。

        极强的扩展性：现在你有了元数据基类。你可以把 100 个策略装进系统，通过回测找出每个分类下夏普比率（Sharpe Ratio）最高的几个，组成你的最终出战阵容！
        """
        import yfinance as yf
        import warnings

        warnings.filterwarnings('ignore')

        print("下载测试数据中...")
        # 下载上证指数 (大盘标杆) 和 贵州茅台 (目标个股)
        sh_index = yf.download('000001.SS', start='2022-01-01', end='2024-01-01', progress=False)
        maotai = yf.download('600519.SS', start='2022-01-01', end='2024-01-01', progress=False)

        # 清理多重索引
        sh_index.columns = sh_index.columns.droplevel('Ticker')
        maotai.columns = maotai.columns.droplevel('Ticker')

        # 初始化终极引擎 (传入大盘数据)
        engine = HolyGrailEnsembleEngine(sh_index)

        # 扫描茅台
        engine.run_scan(maotai, "贵州茅台 (600519)")