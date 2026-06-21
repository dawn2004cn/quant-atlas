"""Tests for new architecture services."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.domain.models.signal_models import (
    SignalGenerator,
    SignalType,
    SignalStrength,
    SignalSource,
)
from app.domain.models.portfolio_models import (
    Portfolio,
    Position,
    PositionSide,
    PositionStatus,
)
from app.domain.models.risk_models import (
    RiskCalculator,
    RiskLevel,
)
from app.application.dto.complete_dto import (
    SignalDTO,
    PositionDTO,
    PortfolioDTO,
    RiskAssessmentDTO,
)


class TestSignalGenerator(unittest.TestCase):
    """Test signal generation domain model."""

    def test_generate_breakout_signal(self):
        """Test breakout signal generation."""
        signal = SignalGenerator.generate_breakout_signal(
            code="600519",
            name="贵州茅台",
            price=1800.0,
            volume=1000000,
            high=1820.0,
            low=1780.0,
            open_price=1790.0,
            prev_close=1795.0,
            avg_volume_20d=800000,
        )

        self.assertEqual(signal.code, "600519")
        self.assertEqual(signal.name, "贵州茅台")
        self.assertEqual(signal.signal_type, SignalType.BREAKOUT)
        self.assertIsNotNone(signal.id)

    def test_generate_volume_signal(self):
        """Test volume-based signal."""
        signal = SignalGenerator.generate_volume_signal(
            code="000001",
            name="平安银行",
            price=12.5,
            volume=50000000,
            avg_volume_20d=20000000,
        )

        self.assertEqual(signal.signal_type, SignalType.VOLUME)
        self.assertIn(signal.strength, SignalStrength)

    def test_generate_momentum_signal(self):
        """Test momentum signal."""
        signal = SignalGenerator.generate_momentum_signal(
            code="600036",
            name="招商银行",
            price=35.0,
            change_pct=5.5,
            rsi=72.0,
            macd=0.5,
        )

        self.assertEqual(signal.signal_type, SignalType.MOMENTUM)


class TestPortfolio(unittest.TestCase):
    """Test portfolio domain model."""

    def test_create_portfolio(self):
        """Test portfolio creation."""
        portfolio = Portfolio(
            id="test-portfolio-1",
            name="Test Portfolio",
            initial_capital=100000.0,
        )

        self.assertEqual(portfolio.initial_capital, 100000.0)
        self.assertEqual(portfolio.current_capital, 100000.0)
        self.assertEqual(len(portfolio.positions), 0)

    def test_add_position(self):
        """Test adding position to portfolio."""
        portfolio = Portfolio(
            id="test-portfolio-1",
            name="Test",
            initial_capital=100000.0,
        )

        position = Position(
            id="pos-1",
            code="600519",
            name="贵州茅台",
            quantity=100,
            avg_cost=1700.0,
        )
        position.current_price = 1800.0

        portfolio.add_position(position)

        self.assertEqual(len(portfolio.positions), 1)
        self.assertEqual(portfolio.positions[0].code, "600519")

    def test_portfolio_pnl(self):
        """Test portfolio PnL calculation."""
        portfolio = Portfolio(
            id="test-portfolio-1",
            name="Test",
            initial_capital=100000.0,
        )

        position = Position(
            id="pos-1",
            code="600519",
            quantity=100,
            avg_cost=1700.0,
            current_price=1800.0,
        )
        portfolio.add_position(position)

        self.assertEqual(portfolio.total_pnl, 10000.0)
        self.assertAlmostEqual(portfolio.pnl_pct, 10.0, 1)


class TestRiskCalculator(unittest.TestCase):
    """Test risk calculation domain model."""

    def test_calculate_position_risk(self):
        """Test position risk calculation."""
        risk = RiskCalculator.calculate_position_risk(
            position_value=50000.0,
            portfolio_value=100000.0,
            weight=0.5,
            volatility=0.25,
            sector="consumer",
        )

        self.assertIsNotNone(risk.risk_score)
        self.assertIsNotNone(risk.risk_level)
        self.assertIn(risk.risk_level, RiskLevel)

    def test_calculate_portfolio_risk(self):
        """Test portfolio risk calculation."""
        positions = [
            {"code": "600519", "value": 30000, "weight": 0.3, "volatility": 0.25},
            {"code": "000001", "value": 20000, "weight": 0.2, "volatility": 0.30},
        ]

        risk = RiskCalculator.calculate_portfolio_risk(
            positions=positions,
            total_value=100000.0,
            confidence_level=0.95,
        )

        self.assertIsNotNone(risk.risk_score)
        self.assertIsNotNone(risk.value_at_risk)


class TestDTOs(unittest.TestCase):
    """Test DTO classes."""

    def test_signal_dto(self):
        """Test SignalDTO."""
        dto = SignalDTO(
            code="600519",
            name="贵州茅台",
            signal_type="breakout",
            direction="long",
            strength="strong",
            price=1800.0,
            confidence=75.0,
        )

        self.assertEqual(dto.code, "600519")
        self.assertEqual(dto.signal_type, "breakout")

    def test_position_dto(self):
        """Test PositionDTO."""
        dto = PositionDTO(
            code="600519",
            name="贵州茅台",
            quantity=100,
            avg_cost=1700.0,
            current_price=1800.0,
            side="long",
        )

        self.assertEqual(dto.pnl, 10000.0)
        self.assertAlmostEqual(dto.pnl_pct, 5.88, 1)

    def test_portfolio_dto(self):
        """Test PortfolioDTO."""
        dto = PortfolioDTO(
            id="test-1",
            name="Test Portfolio",
            initial_capital=100000.0,
            current_capital=110000.0,
            positions=[],
        )

        self.assertEqual(dto.current_capital, 110000.0)


class TestEventBus(unittest.TestCase):
    """Test event bus functionality."""

    def test_publish_event(self):
        """Test publishing and subscribing to events."""
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