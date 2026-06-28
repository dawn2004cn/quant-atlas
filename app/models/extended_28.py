from __future__ import annotations

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, ADXIndicator, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands, DonchianChannel, KeltnerChannel
from ta.volume import ChaikinMoneyFlowIndicator, MFIIndicator, OnBalanceVolumeIndicator

from ..core.base_strategy import BaseTradingStrategy
from ..core.kdj import tdx_k_d


def _safe(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


class _ExtBase(BaseTradingStrategy):
    @property
    def principle(self) -> str:
        return "扩展策略库：以轻量技术指标为主，便于解释与快速迭代。"


# ==========================================
# 📈 扩展 01-10：趋势突破 / 动量
# ==========================================
class EXT01_EMA_Cross_10_30(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT01. EMA(10/30) 金叉"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "EMA10 上穿 EMA30 做多；下穿退出。"

    def get_start_idx(self) -> int:
        return 40

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        ema10 = EMAIndicator(df["Close"], 10).ema_indicator()
        ema30 = EMAIndicator(df["Close"], 30).ema_indicator()
        buy = (ema10 > ema30) & (ema10.shift(1) <= ema30.shift(1))
        sell = (ema10 < ema30) & (ema10.shift(1) >= ema30.shift(1))
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT02_Donchian_20_Breakout(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT02. 唐奇安(20) 上轨突破"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "收盘突破 20 日上轨做多；跌破中轨/下轨退出（简化：跌破中轨）。"

    def get_start_idx(self) -> int:
        return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        dc = DonchianChannel(df["High"], df["Low"], df["Close"], window=20)
        up = dc.donchian_channel_hband()
        mid = dc.donchian_channel_mband()
        close = _safe(df["Close"])
        buy = close > up.shift(1)
        sell = close < mid
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT03_Keltner_Breakout(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT03. Keltner 上轨突破"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "收盘上破 KC 上轨做多；跌回中轨退出。"

    def get_start_idx(self) -> int:
        return 35

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        kc = KeltnerChannel(df["High"], df["Low"], df["Close"], window=20)
        up = kc.keltner_channel_hband()
        mid = kc.keltner_channel_mband()
        close = _safe(df["Close"])
        buy = close > up.shift(1)
        sell = close < mid
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT04_ADX_DI_Trend(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT04. ADX 趋势确认(+DI)"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "ADX>20 且 +DI>-DI 做多；反转或 ADX 走弱退出。"

    def get_start_idx(self) -> int:
        return 35

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        adx = ADXIndicator(df["High"], df["Low"], df["Close"], window=14)
        a = adx.adx()
        p = adx.adx_pos()
        n = adx.adx_neg()
        buy = (a > 20) & (p > n)
        sell = (p < n) | (a < 18)
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT05_MACD_Hist_Acceleration(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT05. MACD 柱体加速"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "MACD 柱体连续走强且 DIF>DEA 做多；柱体转弱退出。"

    def get_start_idx(self) -> int:
        return 40

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        m = MACD(df["Close"])
        dif = m.macd()
        dea = m.macd_signal()
        hist = m.macd_diff()
        accel = (hist > hist.shift(1)) & (hist.shift(1) > hist.shift(2))
        buy = accel & (dif > dea) & (hist > 0)
        sell = (dif < dea) | (hist < hist.shift(1))
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT06_EMA_Pullback_5_20(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT06. EMA(5) 回踩 EMA(20)"

    @property
    def category(self) -> str:
        return "动量回调"

    @property
    def description(self) -> str:
        return "趋势中回踩：Close 触碰 EMA20 后收回并站上 EMA5 做多；跌破 EMA20 退出。"

    def get_start_idx(self) -> int:
        return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        close = _safe(df["Close"])
        ema5 = EMAIndicator(close, 5).ema_indicator()
        ema20 = EMAIndicator(close, 20).ema_indicator()
        touch = (close <= ema20 * 1.005) & (close >= ema20 * 0.985)
        buy = touch & (close > ema5) & (ema20 > ema20.shift(5))
        sell = close < ema20
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT07_BB_Squeeze_Breakout(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT07. 布林收敛后突破"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "布林带宽低位收敛后，上破上轨做多；跌回中轨退出。"

    def get_start_idx(self) -> int:
        return 60

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        bb = BollingerBands(df["Close"], window=20, window_dev=2)
        up = bb.bollinger_hband()
        mid = bb.bollinger_mavg()
        width = (up - bb.bollinger_lband()) / mid.replace(0, np.nan)
        squeeze = width < width.rolling(60).quantile(0.25)
        close = _safe(df["Close"])
        buy = squeeze & (close > up.shift(1))
        sell = close < mid
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT08_ATR_Channel_Breakout(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT08. ATR 通道突破"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "Close 上破 SMA20+2*ATR 做多；跌回 SMA20 退出。"

    def get_start_idx(self) -> int:
        return 40

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        atr = AverageTrueRange(df["High"], df["Low"], df["Close"], window=14).average_true_range()
        sma20 = SMAIndicator(df["Close"], 20).sma_indicator()
        upper = sma20 + 2.0 * atr
        close = _safe(df["Close"])
        buy = close > upper.shift(1)
        sell = close < sma20
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT09_VWMA_Trend(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT09. VWMA 趋势确认"

    @property
    def category(self) -> str:
        return "机构资金"

    @property
    def description(self) -> str:
        return "Close 上穿 VWMA20 且 VWMA 上行做多；跌破 VWMA 退出。"

    def get_start_idx(self) -> int:
        return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        close = _safe(df["Close"])
        vol = _safe(df["Volume"]).replace(0, np.nan)
        vwma = (close * vol).rolling(20).sum() / vol.rolling(20).sum()
        buy = (close > vwma) & (close.shift(1) <= vwma.shift(1)) & (vwma > vwma.shift(5))
        sell = close < vwma
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT10_OBV_Breakout(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT10. OBV 放量突破"

    @property
    def category(self) -> str:
        return "机构资金"

    @property
    def description(self) -> str:
        return "OBV 创 30 日新高且价格站上 MA20 做多；跌破 MA20 退出。"

    def get_start_idx(self) -> int:
        return 35

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        obv = OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
        ma20 = SMAIndicator(df["Close"], 20).sma_indicator()
        close = _safe(df["Close"])
        buy = (obv > obv.rolling(30).max().shift(1)) & (close > ma20)
        sell = close < ma20
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


# ==========================================
# ⚖️ 扩展 11-20：均值回归 / 震荡波段
# ==========================================
class EXT11_RSI2_Reversion(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT11. RSI(2) 超短回归"

    @property
    def category(self) -> str:
        return "均值回归"

    @property
    def description(self) -> str:
        return "RSI2<10 做多；RSI2>70 退出。"

    def get_start_idx(self) -> int:
        return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        r = RSIIndicator(df["Close"], 2).rsi()
        buy = r < 10
        sell = r > 70
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT12_ZScore_10_Reversion(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT12. ZScore(10) 回归"

    @property
    def category(self) -> str:
        return "均值回归"

    @property
    def description(self) -> str:
        return "Close 距离 MA10 超过 -1.8σ 做多；回到均值附近退出。"

    def get_start_idx(self) -> int:
        return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        close = _safe(df["Close"])
        mu = close.rolling(10).mean()
        sd = close.rolling(10).std().replace(0, np.nan)
        z = (close - mu) / sd
        buy = z < -1.8
        sell = z > -0.2
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT13_BB_Lower_Touch(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT13. 布林下轨触碰回归"

    @property
    def category(self) -> str:
        return "震荡波段"

    @property
    def description(self) -> str:
        return "Close 触碰下轨做多；回到中轨退出。"

    def get_start_idx(self) -> int:
        return 30

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        bb = BollingerBands(df["Close"], 20, 2)
        low = bb.bollinger_lband()
        mid = bb.bollinger_mavg()
        close = _safe(df["Close"])
        buy = close < low
        sell = close > mid
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT14_StochSwing(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT14. 随机指标摆动(KD)"

    @property
    def category(self) -> str:
        return "震荡波段"

    @property
    def description(self) -> str:
        return "K 上穿 D 且 K<20 做多；K 下穿 D 且 K>80 退出。"

    def get_start_idx(self) -> int:
        return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        st = StochasticOscillator(df["High"], df["Low"], df["Close"], window=9, smooth_window=3)
        k, d = tdx_k_d(st)
        buy = (k < 20) & (k > d) & (k.shift(1) <= d.shift(1))
        sell = (k > 80) & (k < d) & (k.shift(1) >= d.shift(1))
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT15_KC_MeanReversion(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT15. Keltner 下轨回归"

    @property
    def category(self) -> str:
        return "均值回归"

    @property
    def description(self) -> str:
        return "Close 跌破 KC 下轨做多；回到中轨退出。"

    def get_start_idx(self) -> int:
        return 35

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        kc = KeltnerChannel(df["High"], df["Low"], df["Close"], window=20)
        low = kc.keltner_channel_lband()
        mid = kc.keltner_channel_mband()
        close = _safe(df["Close"])
        buy = close < low
        sell = close > mid
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT16_RSI_MA_Filter(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT16. RSI 回归 + 均线过滤"

    @property
    def category(self) -> str:
        return "均值回归"

    @property
    def description(self) -> str:
        return "Close>MA60 且 RSI14<30 做多；RSI>55 或跌破 MA60 退出。"

    def get_start_idx(self) -> int:
        return 70

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        rsi = RSIIndicator(df["Close"], 14).rsi()
        ma60 = SMAIndicator(df["Close"], 60).sma_indicator()
        close = _safe(df["Close"])
        buy = (close > ma60) & (rsi < 30)
        sell = (rsi > 55) | (close < ma60)
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT17_ATR_Clamp_Reversion(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT17. ATR 过度波动回归"

    @property
    def category(self) -> str:
        return "震荡波段"

    @property
    def description(self) -> str:
        return "当日振幅/ATR 过大后次日反弹（简化：Close 跌破下轨后回归）。"

    def get_start_idx(self) -> int:
        return 40

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        atr = AverageTrueRange(df["High"], df["Low"], df["Close"], window=14).average_true_range()
        ma20 = SMAIndicator(df["Close"], 20).sma_indicator()
        close = _safe(df["Close"])
        lower = ma20 - 2.0 * atr
        buy = close < lower
        sell = close > ma20
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT18_MFI_Reversion(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT18. MFI 资金流超卖回归"

    @property
    def category(self) -> str:
        return "均值回归"

    @property
    def description(self) -> str:
        return "MFI<20 超卖做多；MFI>60 退出。"

    def get_start_idx(self) -> int:
        return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        mfi = MFIIndicator(df["High"], df["Low"], df["Close"], df["Volume"], window=14).money_flow_index()
        buy = mfi < 20
        sell = mfi > 60
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT19_CMF_Breakout(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT19. CMF 资金流转强"

    @property
    def category(self) -> str:
        return "机构资金"

    @property
    def description(self) -> str:
        return "CMF 上穿 0 且价格站上 MA20 做多；CMF 转负退出。"

    def get_start_idx(self) -> int:
        return 35

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        cmf = ChaikinMoneyFlowIndicator(df["High"], df["Low"], df["Close"], df["Volume"], window=20).chaikin_money_flow()
        ma20 = SMAIndicator(df["Close"], 20).sma_indicator()
        close = _safe(df["Close"])
        buy = (cmf > 0) & (cmf.shift(1) <= 0) & (close > ma20)
        sell = cmf < 0
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT20_MA_Slope_Trend(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT20. MA60 斜率趋势"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "MA60 斜率为正且 Close>MA20 做多；跌破 MA20 退出。"

    def get_start_idx(self) -> int:
        return 70

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        ma20 = SMAIndicator(df["Close"], 20).sma_indicator()
        ma60 = SMAIndicator(df["Close"], 60).sma_indicator()
        close = _safe(df["Close"])
        slope = ma60 - ma60.shift(10)
        buy = (slope > 0) & (close > ma20)
        sell = close < ma20
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


# ==========================================
# 🩸 扩展 21-28：恐慌抄底 / 反转
# ==========================================
class EXT21_Gap_Down_Reversal(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT21. 跳空下跌反转"

    @property
    def category(self) -> str:
        return "恐慌抄底"

    @property
    def description(self) -> str:
        return "开盘大幅低开但收盘翻红，视为恐慌出清后反转。"

    def get_start_idx(self) -> int:
        return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        close = _safe(df["Close"])
        open_ = _safe(df["Open"])
        prev_close = close.shift(1)
        gap_down = (open_ - prev_close) / prev_close.replace(0, np.nan) < -0.03
        reversal = close > open_
        buy = gap_down & reversal
        sell = close < SMAIndicator(close, 10).sma_indicator()
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT22_Hammer_Like(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT22. 锤子线近似反转"

    @property
    def category(self) -> str:
        return "恐慌抄底"

    @property
    def description(self) -> str:
        return "下影线显著长于实体，且收盘靠近高点；视为止跌信号。"

    def get_start_idx(self) -> int:
        return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        o = _safe(df["Open"])
        h = _safe(df["High"])
        l = _safe(df["Low"])
        c = _safe(df["Close"])
        body = (c - o).abs()
        lower_shadow = (np.minimum(o, c) - l).clip(lower=0)
        upper_shadow = (h - np.maximum(o, c)).clip(lower=0)
        hammer = (lower_shadow > body * 2.0) & (upper_shadow < body * 0.6) & (c > o)
        buy = hammer
        sell = c < SMAIndicator(c, 10).sma_indicator()
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT23_RSI14_Turn_Up(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT23. RSI14 极弱拐头"

    @property
    def category(self) -> str:
        return "恐慌抄底"

    @property
    def description(self) -> str:
        return "RSI<20 后拐头向上做多；RSI>50 或下破 MA10 退出。"

    def get_start_idx(self) -> int:
        return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        rsi = RSIIndicator(df["Close"], 14).rsi()
        close = _safe(df["Close"])
        ma10 = SMAIndicator(close, 10).sma_indicator()
        buy = (rsi.shift(1) < 20) & (rsi > rsi.shift(1))
        sell = (rsi > 50) | (close < ma10)
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT24_MACD_Zero_Reclaim(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT24. MACD 收复零轴"

    @property
    def category(self) -> str:
        return "恐慌抄底"

    @property
    def description(self) -> str:
        return "DIF 上穿 0 视为趋势恢复；跌回 0 下方退出。"

    def get_start_idx(self) -> int:
        return 50

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        m = MACD(df["Close"])
        dif = m.macd()
        buy = (dif > 0) & (dif.shift(1) <= 0)
        sell = (dif < 0) & (dif.shift(1) >= 0)
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT25_ADX_Reversal(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT25. ADX 趋势衰竭反转"

    @property
    def category(self) -> str:
        return "恐慌抄底"

    @property
    def description(self) -> str:
        return "ADX 高位回落且价格止跌，视为趋势衰竭反转（简化近似）。"

    def get_start_idx(self) -> int:
        return 40

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        adx = ADXIndicator(df["High"], df["Low"], df["Close"], window=14).adx()
        close = _safe(df["Close"])
        ma20 = SMAIndicator(close, 20).sma_indicator()
        buy = (adx.shift(1) > 28) & (adx < adx.shift(1)) & (close > ma20) & (close.shift(1) <= ma20.shift(1))
        sell = close < ma20
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT26_InsideBar_Breakout(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT26. Inside Bar 突破"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "内包线后上破母K高点做多；跌破母K低点退出。"

    def get_start_idx(self) -> int:
        return 25

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        h = _safe(df["High"])
        l = _safe(df["Low"])
        inside = (h < h.shift(1)) & (l > l.shift(1))
        buy = inside.shift(1) & (h > h.shift(1))
        sell = l < l.shift(1)
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT27_ThreeDay_Reversal(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT27. 三日反转"

    @property
    def category(self) -> str:
        return "恐慌抄底"

    @property
    def description(self) -> str:
        return "连续下跌后出现两日企稳+反包，视为反转。"

    def get_start_idx(self) -> int:
        return 20

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        c = _safe(df["Close"])
        down2 = (c.shift(2) > c.shift(1)) & (c.shift(1) > c)
        engulf = (c > c.shift(1)) & (c.shift(1) > c.shift(2))
        buy = down2 & engulf
        sell = c < SMAIndicator(c, 10).sma_indicator()
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


class EXT28_Volume_Spike_Breakout(_ExtBase):
    @property
    def name(self) -> str:
        return "EXT28. 放量突破 MA60"

    @property
    def category(self) -> str:
        return "趋势突破"

    @property
    def description(self) -> str:
        return "成交量放大且收盘上穿 MA60 做多；跌破 MA20 退出。"

    def get_start_idx(self) -> int:
        return 80

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Signal"] = 0
        close = _safe(df["Close"])
        vol = _safe(df["Volume"])
        ma20 = SMAIndicator(close, 20).sma_indicator()
        ma60 = SMAIndicator(close, 60).sma_indicator()
        vol_ma = vol.rolling(10).mean()
        vol_ok = vol > vol_ma * 1.8
        buy = vol_ok & (close > ma60) & (close.shift(1) <= ma60.shift(1))
        sell = close < ma20
        df.loc[buy, "Signal"] = 1
        df.loc[sell, "Signal"] = -1
        return df


def build_extended_28_registry() -> dict[str, type[BaseTradingStrategy]]:
    return {
        "EXT01": EXT01_EMA_Cross_10_30,
        "EXT02": EXT02_Donchian_20_Breakout,
        "EXT03": EXT03_Keltner_Breakout,
        "EXT04": EXT04_ADX_DI_Trend,
        "EXT05": EXT05_MACD_Hist_Acceleration,
        "EXT06": EXT06_EMA_Pullback_5_20,
        "EXT07": EXT07_BB_Squeeze_Breakout,
        "EXT08": EXT08_ATR_Channel_Breakout,
        "EXT09": EXT09_VWMA_Trend,
        "EXT10": EXT10_OBV_Breakout,
        "EXT11": EXT11_RSI2_Reversion,
        "EXT12": EXT12_ZScore_10_Reversion,
        "EXT13": EXT13_BB_Lower_Touch,
        "EXT14": EXT14_StochSwing,
        "EXT15": EXT15_KC_MeanReversion,
        "EXT16": EXT16_RSI_MA_Filter,
        "EXT17": EXT17_ATR_Clamp_Reversion,
        "EXT18": EXT18_MFI_Reversion,
        "EXT19": EXT19_CMF_Breakout,
        "EXT20": EXT20_MA_Slope_Trend,
        "EXT21": EXT21_Gap_Down_Reversal,
        "EXT22": EXT22_Hammer_Like,
        "EXT23": EXT23_RSI14_Turn_Up,
        "EXT24": EXT24_MACD_Zero_Reclaim,
        "EXT25": EXT25_ADX_Reversal,
        "EXT26": EXT26_InsideBar_Breakout,
        "EXT27": EXT27_ThreeDay_Reversal,
        "EXT28": EXT28_Volume_Spike_Breakout,
    }

