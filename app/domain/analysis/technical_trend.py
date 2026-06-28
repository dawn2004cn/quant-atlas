from __future__ import annotations
"""Technical trend analysis - pure domain logic."""



import pandas as pd

from ...core.logger import get_logger
from ...domain.entities import TrendAnalysisResult
from ...domain.enums import TrendStatus



logger = get_logger(__name__)


class TechnicalTrendService:
    """
    Stock trend analysis service.

    Principles:
    1. Trend - MA5>MA10>MA20 bullish alignment
    2. Bias detection - avoid chasing, don't buy when偏离 MA5 exceeds threshold
    3. Volume analysis - prefer volume shrink callbacks
    4. Entry point - MA5/MA10 support
    """

    VOLUME_SHRINK_RATIO = 0.7
    VOLUME_HEAVY_RATIO = 1.5
    MA_SUPPORT_TOLERANCE = 0.02

    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9

    RSI_SHORT = 6
    RSI_MID = 12
    RSI_LONG = 24
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30

    def analyze(self, df: pd.DataFrame, code: str) -> TrendAnalysisResult:
        """Analyze stock trend."""
        if df is None or df.empty or len(df) < 20:
            logger.warning(f"{code} insufficient data for trend analysis")
            return TrendAnalysisResult(
                code=code,
                current_price=0.0,
                ma5=0.0,
                ma10=0.0,
                ma20=0.0,
                bias_ma5=0.0,
                trend_status=TrendStatus.CONSOLIDATION,
                signals=["数据不足"],
            )

        df = df.copy()
        col_map = {col.lower(): col for col in df.columns}
        if "close" in col_map and col_map["close"] != "close":
            df["close"] = df[col_map["close"]]
        if "volume" in col_map and col_map["volume"] != "volume":
            df["volume"] = df[col_map["volume"]]

        df["MA5"] = df["close"].rolling(window=5).mean()
        df["MA10"] = df["close"].rolling(window=10).mean()
        df["MA20"] = df["close"].rolling(window=20).mean()

        ema_fast = df["close"].ewm(span=self.MACD_FAST, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.MACD_SLOW, adjust=False).mean()
        df["MACD_DIF"] = ema_fast - ema_slow
        df["MACD_DEA"] = df["MACD_DIF"].ewm(span=self.MACD_SIGNAL, adjust=False).mean()
        df["MACD_BAR"] = (df["MACD_DIF"] - df["MACD_DEA"]) * 2

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=self.RSI_MID).mean()
        avg_loss = loss.rolling(window=self.RSI_MID).mean()
        rs = avg_gain / avg_loss
        df["RSI_12"] = 100 - (100 / (1 + rs))

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        current_price = float(latest["close"])
        ma5 = float(latest["MA5"])
        ma10 = float(latest["MA10"])
        ma20 = float(latest["MA20"])
        bias_ma5 = (current_price - ma5) / ma5 * 100 if ma5 > 0 else 0.0

        signals = []
        support_levels = []
        resistance_levels = []

        trend_status = TrendStatus.CONSOLIDATION
        if ma5 > ma10 > ma20:
            trend_status = TrendStatus.BULL
            signals.append("多头排列")
        elif ma5 < ma10 < ma20:
            trend_status = TrendStatus.BEAR
            signals.append("空头排列")

        vol_5d_avg = df["volume"].iloc[-6:-1].mean()
        vol_ratio = float(latest["volume"]) / vol_5d_avg if vol_5d_avg > 0 else 1.0
        if vol_ratio >= self.VOLUME_HEAVY_RATIO:
            signals.append("放量")
        elif vol_ratio <= self.VOLUME_SHRINK_RATIO:
            signals.append("缩量")

        if abs(current_price - ma5) / ma5 <= self.MA_SUPPORT_TOLERANCE:
            support_levels.append(ma5)
            signals.append("MA5支撑")
        if abs(current_price - ma10) / ma10 <= self.MA_SUPPORT_TOLERANCE:
            support_levels.append(ma10)
            signals.append("MA10支撑")

        curr_dif_dea = latest["MACD_DIF"] - latest["MACD_DEA"]
        prev_dif_dea = prev["MACD_DIF"] - prev["MACD_DEA"]
        if prev_dif_dea <= 0 and curr_dif_dea > 0:
            signals.append("MACD金叉")
        elif prev_dif_dea >= 0 and curr_dif_dea < 0:
            signals.append("MACD死叉")

        return TrendAnalysisResult(
            code=code,
            current_price=current_price,
            ma5=ma5,
            ma10=ma10,
            ma20=ma20,
            bias_ma5=bias_ma5,
            trend_status=trend_status,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            signals=signals,
        )
