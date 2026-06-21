"""Tests for domain/enums.py — MarketCode and other domain enums."""

from __future__ import annotations

from app.domain.enums import (
    BuySignal,
    MACDStatus,
    MarketCode,
    RSIStatus,
    TrendStatus,
    VolumeStatus,
)


class TestMarketCode:
    """Tests for the MarketCode enum."""

    def test_has_cn(self):
        assert hasattr(MarketCode, "CN")

    def test_has_hk(self):
        assert hasattr(MarketCode, "HK")

    def test_has_us(self):
        assert hasattr(MarketCode, "US")

    def test_has_crypto(self):
        assert hasattr(MarketCode, "CRYPTO")

    def test_has_sh_sz(self):
        assert hasattr(MarketCode, "SH")
        assert hasattr(MarketCode, "SZ")

    def test_benchmark_property(self):
        assert MarketCode.CN.benchmark == "000300"
        assert MarketCode.US.benchmark == "SPY"

    def test_currency_property(self):
        assert MarketCode.CN.currency == "CNY"
        assert MarketCode.US.currency == "USD"


class TestTrendStatus:
    """Tests for the TrendStatus enum."""

    def test_has_bullish_values(self):
        assert hasattr(TrendStatus, "STRONG_BULL")
        assert hasattr(TrendStatus, "BULL")
        assert hasattr(TrendStatus, "WEAK_BULL")

    def test_has_chinese_values(self):
        assert any("多头" in s.value for s in TrendStatus)
        assert any("空头" in s.value for s in TrendStatus)
        assert any("盘整" in s.value for s in TrendStatus)


class TestVolumeStatus:
    """Tests for the VolumeStatus enum."""

    def test_has_values(self):
        assert hasattr(VolumeStatus, "HEAVY_VOLUME_UP")
        assert hasattr(VolumeStatus, "HEAVY_VOLUME_DOWN")
        assert hasattr(VolumeStatus, "NORMAL")

    def test_has_chinese_values(self):
        assert any("放量" in v.value for v in VolumeStatus)
        assert any("缩量" in v.value for v in VolumeStatus)


class TestBuySignal:
    """Tests for the BuySignal enum."""

    def test_has_values(self):
        assert hasattr(BuySignal, "STRONG_BUY")
        assert hasattr(BuySignal, "BUY")
        assert hasattr(BuySignal, "HOLD")
        assert hasattr(BuySignal, "SELL")
        assert hasattr(BuySignal, "STRONG_SELL")

    def test_has_chinese_values(self):
        assert any("买入" in s.value for s in BuySignal)
        assert any("卖出" in s.value for s in BuySignal)


class TestMACDStatus:
    """Tests for the MACDStatus enum."""

    def test_has_values(self):
        assert hasattr(MACDStatus, "GOLDEN_CROSS")
        assert hasattr(MACDStatus, "DEATH_CROSS")
        assert hasattr(MACDStatus, "BULLISH")
        assert hasattr(MACDStatus, "BEARISH")

    def test_has_chinese_values(self):
        assert any("金叉" in s.value for s in MACDStatus)
        assert any("死叉" in s.value for s in MACDStatus)


class TestRSIStatus:
    """Tests for the RSIStatus enum."""

    def test_has_values(self):
        assert hasattr(RSIStatus, "OVERBOUGHT")
        assert hasattr(RSIStatus, "OVERSOLD")
        assert hasattr(RSIStatus, "NEUTRAL")

    def test_has_chinese_values(self):
        assert any("超买" in s.value for s in RSIStatus)
        assert any("超卖" in s.value for s in RSIStatus)
