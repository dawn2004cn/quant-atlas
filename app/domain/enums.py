"""Domain enumerations."""

from enum import Enum


class MarketCode(str, Enum):
    """Supported market identifiers."""

    CN = "CN"
    US = "US"
    HK = "HK"
    CRYPTO = "CRYPTO"
    FX = "FX"
    FUTURES = "FUTURES"
    SH = "SH"
    SZ = "SZ"
    BJ = "BJ"

    @property
    def benchmark(self) -> str:
        """Get benchmark symbol for this market."""
        return MARKET_BENCHMARKS.get(self, "SPY")

    @property
    def currency(self) -> str:
        """Get currency code for this market."""
        return MARKET_CURRENCIES.get(self, "USD")


MARKET_BENCHMARKS = {
    MarketCode.CN: "000300",
    MarketCode.US: "SPY",
    MarketCode.HK: "0700.HK",
    MarketCode.CRYPTO: "BTCUSDT",
    MarketCode.FX: "USDCNY",
    MarketCode.FUTURES: "IF888",
    MarketCode.SH: "000001",
    MarketCode.SZ: "399001",
    MarketCode.BJ: "899050",
}

MARKET_CURRENCIES = {
    MarketCode.CN: "CNY",
    MarketCode.US: "USD",
    MarketCode.HK: "HKD",
    MarketCode.CRYPTO: "USDT",
    MarketCode.FX: "USD",
    MarketCode.FUTURES: "CNY",
    MarketCode.SH: "CNY",
    MarketCode.SZ: "CNY",
    MarketCode.BJ: "CNY",
}


class TrendStatus(str, Enum):
    """趋势状态枚举"""

    STRONG_BULL = "强势多头"
    BULL = "多头排列"
    WEAK_BULL = "弱势多头"
    CONSOLIDATION = "盘整"
    WEAK_BEAR = "弱势空头"
    BEAR = "空头排列"
    STRONG_BEAR = "强势空头"


class VolumeStatus(str, Enum):
    """量能状态枚举"""

    HEAVY_VOLUME_UP = "放量上涨"
    HEAVY_VOLUME_DOWN = "放量下跌"
    SHRINK_VOLUME_UP = "缩量上涨"
    SHRINK_VOLUME_DOWN = "缩量回调"
    NORMAL = "量能正常"


class BuySignal(str, Enum):
    """买入信号枚举"""

    STRONG_BUY = "强烈买入"
    BUY = "买入"
    HOLD = "持有"
    WAIT = "观望"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"


class MACDStatus(str, Enum):
    """MACD状态枚举"""

    GOLDEN_CROSS_ZERO = "零轴上金叉"
    GOLDEN_CROSS = "金叉"
    BULLISH = "多头"
    CROSSING_UP = "上穿零轴"
    CROSSING_DOWN = "下穿零轴"
    BEARISH = "空头"
    DEATH_CROSS = "死叉"


class RSIStatus(str, Enum):
    """RSI状态枚举"""

    OVERBOUGHT = "超买"
    STRONG_BUY = "强势买入"
    NEUTRAL = "中性"
    WEAK = "弱势"
    OVERSOLD = "超卖"
