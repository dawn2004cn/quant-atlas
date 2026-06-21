"""Comprehensive integration tests for new architecture."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.domain.models import (
    RiskCalculator,
    SignalGenerator,
    Portfolio,
    MarketAnalyzer,
    CalendarService,
    TrendDirection,
    MarketRegime,
)
from app.domain.models.analysis_models import (
    TechnicalIndicators,
    Analyzer,
    AnalysisService,
)


class TestMarketModels(unittest.TestCase):
    """Test market domain models."""

    def test_market_regime_detection(self):
        """Test market regime detection."""
        rising_prices = [100 + i * 2 for i in range(30)]
        regime = MarketAnalyzer.detect_regime(rising_prices)
        self.assertEqual(regime, MarketRegime.BULL)

        falling_prices = [100 - i * 2 for i in range(30)]
        regime = MarketAnalyzer.detect_regime(falling_prices)
        self.assertEqual(regime, MarketRegime.BEAR)

        sideways_prices = [100 + (i % 3 - 1) for i in range(30)]
        regime = MarketAnalyzer.detect_regime(sideways_prices)
        self.assertIn(regime, [MarketRegime.SIDEWAYS, MarketRegime.RECOVERY])

    def test_calendar_service(self):
        """Test trading calendar."""
        monday = datetime(2024, 1, 8)
        self.assertTrue(CalendarService.is_trading_day(monday))

        saturday = datetime(2024, 1, 6)
        self.assertFalse(CalendarService.is_trading_day(saturday))

    def test_market_sentiment(self):
        """Test market sentiment calculation."""
        stocks = [
            {"change_pct": 5.0},
            {"change_pct": 3.0},
            {"change_pct": -2.0},
            {"change_pct": -1.0},
            {"change_pct": 0},
        ]
        sentiment = MarketAnalyzer.calculate_market_sentiment(stocks)
        self.assertEqual(sentiment.up_count, 2)
        self.assertEqual(sentiment.down_count, 2)
        self.assertEqual(sentiment.flat_count, 1)


class TestAnalysisModels(unittest.TestCase):
    """Test analysis domain models."""

    def test_technical_indicators(self):
        """Test technical indicators."""
        indicators = TechnicalIndicators(code="600519")
        indicators.ma5 = 1800
        indicators.ma20 = 1750
        indicators.rsi = 65
        indicators.macd = 10

        trend = Analyzer.calculate_trend(indicators)
        self.assertEqual(trend, TrendDirection.UP)

        momentum = Analyzer.calculate_momentum(indicators)
        self.assertGreater(momentum, 0)

    def test_support_resistance_levels(self):
        """Test support and resistance detection."""
        prices = [100, 105, 102, 108, 103, 110, 105, 112, 106, 115, 107]

        supports = Analyzer.find_support_levels(prices)
        self.assertIsInstance(supports, list)

        resistances = Analyzer.find_resistance_levels(prices)
        self.assertIsInstance(resistances, list)

    def test_fibonacci_levels(self):
        """Test Fibonacci calculation."""
        levels = Analyzer.calculate_fibonacci_levels(100, 80)
        self.assertIn("50%", levels)
        self.assertIn("61.8%", levels)
        self.assertAlmostEqual(levels["61.8%"], 92.36, 1)

    def test_analysis_service(self):
        """Test complete analysis service."""
        indicators = TechnicalIndicators(code="600519")
        indicators.ma5 = 1800
        indicators.ma20 = 1750
        indicators.ma60 = 1700
        indicators.rsi = 60
        indicators.macd = 5

        result = AnalysisService.analyze_stock(
            code="600519",
            name="贵州茅台",
            price=1800,
            indicators=indicators,
        )

        self.assertEqual(result.code, "600519")
        self.assertIn(result.recommendation, ["strong_buy", "buy", "hold", "sell", "strong_sell"])
        self.assertGreater(result.overall_score, 0)
        self.assertLessEqual(result.overall_score, 100)


class TestSignalModels(unittest.TestCase):
    """Test signal domain models."""

    def test_breakout_signal(self):
        """Test breakout signal generation."""
        signal = SignalGenerator.generate_breakout_signal(
            code="600519",
            name="贵州茅台",
            price=1800,
            volume=1000000,
            high=1820,
            low=1780,
            open_price=1790,
            prev_close=1795,
            avg_volume_20d=800000,
        )

        self.assertIsNotNone(signal.id)
        self.assertEqual(signal.code, "600519")
        self.assertIsNotNone(signal.strength)

    def test_volume_signal(self):
        """Test volume signal generation."""
        signal = SignalGenerator.generate_volume_signal(
            code="000001",
            name="平安银行",
            price=12.5,
            volume=50000000,
            avg_volume_20d=20000000,
        )

        self.assertIsNotNone(signal)

    def test_momentum_signal(self):
        """Test momentum signal generation."""
        signal = SignalGenerator.generate_momentum_signal(
            code="600036",
            name="招商银行",
            price=35,
            change_pct=5.5,
            rsi=72,
            macd=0.5,
        )

        self.assertIsNotNone(signal)


class TestPortfolioModels(unittest.TestCase):
    """Test portfolio domain models."""

    def test_portfolio_pnl(self):
        """Test portfolio PnL calculation."""
        portfolio = Portfolio(
            id="test-1",
            name="Test",
            initial_capital=100000,
        )

        position = MagicMock()
        position.code = "600519"
        position.quantity = 100
        position.avg_cost = 1700
        position.current_price = 1800
        position.total_cost.return_value = 170000
        position.total_value.return_value = 180000
        position.pnl.return_value = 10000

        portfolio.add_position(position)

        self.assertEqual(len(portfolio.positions), 1)
        self.assertGreater(portfolio.total_pnl, 0)


class TestRiskModels(unittest.TestCase):
    """Test risk domain models."""

    def test_position_risk(self):
        """Test position risk calculation."""
        risk = RiskCalculator.calculate_position_risk(
            position_value=50000,
            portfolio_value=100000,
            weight=0.5,
            volatility=0.25,
        )

        self.assertIsNotNone(risk.risk_score)
        self.assertIsNotNone(risk.risk_level)

    def test_portfolio_risk(self):
        """Test portfolio risk calculation."""
        positions = [
            {"code": "600519", "value": 30000, "weight": 0.3, "volatility": 0.25},
            {"code": "000001", "value": 20000, "weight": 0.2, "volatility": 0.30},
        ]

        risk = RiskCalculator.calculate_portfolio_risk(
            positions=positions,
            total_value=100000,
            confidence_level=0.95,
        )

        self.assertIsNotNone(risk.risk_score)
        self.assertIsNotNone(risk.concentration_risk)


class TestDTOs(unittest.TestCase):
    """Test DTO classes."""

    def test_quote_dto(self):
        """Test QuoteDTO."""
        from app.application.dto.complete_dto import QuoteDTO

        quote = QuoteDTO(
            code="600519",
            name="贵州茅台",
            price=1800,
            change=10,
            change_pct=0.56,
            volume=1000000,
        )

        self.assertEqual(quote.code, "600519")
        self.assertIsNotNone(quote.timestamp)

    def test_signal_dto(self):
        """Test SignalDTO."""
        from app.application.dto.complete_dto import SignalDTO

        signal = SignalDTO(
            code="600519",
            name="贵州茅台",
            signal_type="breakout",
            strength="strong",
            price=1800,
            confidence=75,
        )

        self.assertEqual(signal.signal_type, "breakout")

    def test_portfolio_dto(self):
        """Test PortfolioDTO."""
        from app.application.dto.complete_dto import PortfolioDTO

        portfolio = PortfolioDTO(
            id="test-1",
            name="Test Portfolio",
            initial_capital=100000,
            current_capital=110000,
        )

        self.assertEqual(portfolio.current_capital, 110000)


class TestEventBus(unittest.TestCase):
    """Test event bus functionality."""

    def test_publish_subscribe(self):
        """Test publish and subscribe."""
        from app.application.events import EventBus, EventType

        bus = EventBus()
        received = []

        @bus.subscribe(EventType.SIGNAL_GENERATED)
        def handler(event):
            received.append(event)

        from app.application.events.event_bus import Event
        event = Event(
            type=EventType.SIGNAL_GENERATED,
            payload={"code": "600519"},
            source="test",
        )
        bus.publish(event)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload["code"], "600519")


if __name__ == "__main__":
    unittest.main()