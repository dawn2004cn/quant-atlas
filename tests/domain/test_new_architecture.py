"""Tests for new architecture components."""

import pytest
import asyncio
from datetime import datetime

from app.domain.models import RiskCalculator, RiskMetrics, SignalGenerator, Portfolio
from app.domain.services import RiskDomainService, MarketDomainService
from app.domain.dto import QuoteDTO
from app.application.dto.complete_dto import SignalDTO, APIResponse
from app.application.events import EventBus, EventType, get_event_bus
from app.application.events.event_bus import Event


class TestDomainModels:
    """Test domain models."""

    def test_risk_metrics_from_prices(self):
        """Test risk metrics calculation from price history."""
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        metrics = RiskMetrics.from_price_history(prices)

        assert 0 <= metrics.score <= 100
        assert metrics.level in ['low', 'medium', 'high', 'extreme']

    def test_fibonacci_levels(self):
        """Test Fibonacci level calculation."""
        levels = RiskCalculator.calculate_fibonacci_levels(100, 80)
        assert len(levels) == 5
        assert all(80 <= l.price <= 100 for l in levels)

    def test_signal_evaluation(self):
        """Test signal generation and evaluation."""
        signal = SignalGenerator.generate_breakout_signal(
            '600519', 105.0, 100.0, 1000000, 500000
        )
        assert signal is not None
        assert signal.signal_type.value == 'breakout'

        evaluation = SignalGenerator.evaluate_signal(signal)
        assert 'action' in evaluation


class TestDTOs:
    """Test DTOs."""

    def test_quote_dto(self):
        """Test QuoteDTO."""
        quote = QuoteDTO(
            code='600519',
            name='贵州茅台',
            price=1800.0,
            change_pct=2.5,
            change_amount=0.0,
            volume=0,
            amount=0.0,
            turnover=0.0,
        )
        assert quote.code == '600519'
        assert quote.price == 1800.0

    def test_api_response(self):
        """Test API response wrapper."""
        response = APIResponse.ok({'data': 'test'})
        assert response.success is True

        response = APIResponse.error_response('Error message')
        assert response.success is False
        assert response.error == 'Error message'


class TestEventBus:
    """Test event bus."""

    def test_event_publish_subscribe(self):
        """Test event publish and subscribe."""
        bus = EventBus()
        received = []

        @bus.subscribe(EventType.DATA_SYNCED)
        def handler(event):
            received.append(event)

        event = Event(
            type=EventType.DATA_SYNCED,
            payload={'test': 'data'},
            source='test'
        )
        bus.publish(event)

        assert len(received) == 1
        assert received[0].payload['test'] == 'data'

    def test_event_history(self):
        """Test event history tracking."""
        bus = EventBus()
        bus.publish(Event(type=EventType.DATA_SYNCED, payload={}, source='test'))
        bus.publish(Event(type=EventType.QUOTE_UPDATED, payload={}, source='test'))

        history = bus.get_history(limit=10)
        assert len(history) >= 2


class TestDomainServices:
    """Test domain services."""

    def test_normalize_quote(self):
        """Test quote normalization."""
        raw = {
            'symbol': '600519',
            'name': '贵州茅台',
            'close': 1800.0,
            'pct_chg': 2.5,
            'volume': 1000000
        }
        normalized = MarketDomainService.normalize_quote(raw)

        assert normalized['code'] == '600519'
        assert normalized['price'] == 1800.0
        assert normalized['change_pct'] == 2.5


class TestAsyncComponents:
    """Test async components."""

    def test_async_market_provider_wrapper(self):
        """Test async provider wrapper creation."""
        # This would require a real provider
        # Just test the import works
        from app.infrastructure.providers.async_market_provider import AsyncMarketDataProvider
        assert AsyncMarketDataProvider is not None


def run_tests():
    """Run all tests."""
    import sys
    sys.exit(pytest.main([__file__, '-v']))


if __name__ == '__main__':
    run_tests()