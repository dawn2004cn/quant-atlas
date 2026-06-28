from __future__ import annotations

"""Technical indicator provider with column mapping fix."""


from typing import Any

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, ADXIndicator, CCIIndicator, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import OnBalanceVolumeIndicator

from ...core.kdj import tdx_k_d
from ...core.logger import get_logger
from ...domain.ports import IndicatorProvider

logger = get_logger(__name__)


class TaIndicatorProvider(IndicatorProvider):
    """Use the 'ta' library to calculate technical indicators."""

    def calculate(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate indicators and return latest values."""
        if not history:
            return {}

        frame = pd.DataFrame(history)

        # 🟢 修复处：统一列名映射 (兼容 Close/close, Open/open 等)
        col_map = {col.lower(): col for col in frame.columns}
        def get_col(name):
            return frame[col_map.get(name.lower(), name)]

        try:
            # 提取核心序列并确保数值化
            close = pd.to_numeric(get_col("close"), errors="coerce")
            high = pd.to_numeric(get_col("high"), errors="coerce")
            low = pd.to_numeric(get_col("low"), errors="coerce")

            # 计算常用指标
            res = {}

            # MA/EMA
            res["ma20"] = SMAIndicator(close, window=20).sma_indicator().iloc[-1]
            res["ema12"] = EMAIndicator(close, window=12).ema_indicator().iloc[-1]
            res["ema26"] = EMAIndicator(close, window=26).ema_indicator().iloc[-1]

            # MACD
            macd = MACD(close)
            res["macd"] = macd.macd().iloc[-1]
            res["macd_signal"] = macd.macd_signal().iloc[-1]
            res["macd_diff"] = macd.macd_diff().iloc[-1]

            # RSI
            res["rsi14"] = RSIIndicator(close, window=14).rsi().iloc[-1]

            # KDJ (Stochastic) — 通达信 K/D 与 ta 的 stoch / stoch_signal 对调
            stoch = StochasticOscillator(high, low, close, window=9, smooth_window=3)
            kdj_k, kdj_d = tdx_k_d(stoch)
            res["kdj_k"] = kdj_k.iloc[-1]
            res["kdj_d"] = kdj_d.iloc[-1]
            res["kdj_j"] = (3 * res["kdj_k"]) - (2 * res["kdj_d"])

            # Bollinger Bands
            bb = BollingerBands(close, window=20, window_dev=2.0)
            res["bb_high"] = bb.bollinger_hband().iloc[-1]
            res["bb_mid"] = bb.bollinger_mavg().iloc[-1]
            res["bb_low"] = bb.bollinger_lband().iloc[-1]

            # ATR & ADX
            res["atr"] = AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
            res["adx"] = ADXIndicator(high, low, close, window=14).adx().iloc[-1]

            # CCI
            res["cci"] = CCIIndicator(high, low, close, window=20).cci().iloc[-1]

            # 清理 NaN
            return {k: (0 if pd.isna(v) else float(v)) for k, v in res.items()}

        except Exception as e:
            logger.warning("指标计算失败: %s", e, exc_info=True)
            return {}


class AdvancedTaIndicatorProvider:
    """Extended technical indicators provider for advanced analysis."""

    @staticmethod
    def calc_ma(close: pd.Series, window: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return SMAIndicator(close=close, window=window).sma_indicator()

    @staticmethod
    def calc_ema(close: pd.Series, window: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return EMAIndicator(close=close, window=window).ema_indicator()

    @staticmethod
    def calc_macd(
        close: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD indicator.
        Returns: DIF (fast line), DEA (signal line), MACD (histogram)
        """
        macd_indicator = MACD(
            close=close,
            window_slow=slow_period,
            window_fast=fast_period,
            window_sign=signal_period,
        )
        dif = macd_indicator.macd()
        dea = macd_indicator.macd_signal()
        macd = macd_indicator.macd_diff() * 2
        return dif, dea, macd

    @staticmethod
    def calc_rsi(close: pd.Series, window: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        return RSIIndicator(close=close, window=window).rsi()

    @staticmethod
    def calc_adx(
        high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Average Directional Index."""
        adx_ind = ADXIndicator(high=high, low=low, close=close, window=window)
        return adx_ind.adx(), adx_ind.adx_pos(), adx_ind.adx_neg()

    @staticmethod
    def calc_dmi(
        high: pd.Series, low: pd.Series, close: pd.Series
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate DMI directional indicator.
        Returns: +DI (bullish), -DI (bearish), ADX (trend strength)
        """
        adx_evaluator = ADXIndicator(high=high, low=low, close=close, window=14, fillna=False)
        plus_di = adx_evaluator.adx_pos()
        minus_di = adx_evaluator.adx_neg()
        adx = adx_evaluator.adx()
        return plus_di, minus_di, adx

    @staticmethod
    def calc_cci(
        high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20
    ) -> pd.Series:
        """Calculate Commodity Channel Index."""
        cci = CCIIndicator(high=high, low=low, close=close, window=window)
        return cci.cci()

    @staticmethod
    def calc_kdj(
        high: pd.Series, low: pd.Series, close: pd.Series, window: int = 9, smooth_window: int = 3
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate KDJ stochastic indicator.
        Returns: K, D, J lines
        """
        stoch = StochasticOscillator(
            high=high, low=low, close=close, window=window, smooth_window=smooth_window
        )
        k, d = tdx_k_d(stoch)
        j = 3 * k - 2 * d
        return k, d, j

    @staticmethod
    def calc_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate On Balance Volume."""
        return OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    @staticmethod
    def calc_vol_ratio(volume: pd.Series, window: int = 5) -> pd.Series:
        """Calculate Volume Ratio (current volume / average of past N periods)."""
        past_ma = volume.shift(1).rolling(window=window).mean()
        return volume / past_ma.replace(0, np.nan)

    @staticmethod
    def calc_bias(close: pd.Series, window: int = 20) -> pd.Series:
        """Calculate BIAS (deviation from moving average)."""
        ma = SMAIndicator(close=close, window=window).sma_indicator()
        return (close - ma) / ma.replace(0, np.nan) * 100

    @staticmethod
    def calc_bb(
        close: pd.Series, window: int = 20, dev: float = 2.0
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        bb = BollingerBands(close=close, window=window, window_dev=dev)
        return bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()

    @staticmethod
    def calc_atr(
        high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14
    ) -> pd.Series:
        """Calculate Average True Range."""
        atr = AverageTrueRange(high=high, low=low, close=close, window=window)
        return atr.average_true_range()
