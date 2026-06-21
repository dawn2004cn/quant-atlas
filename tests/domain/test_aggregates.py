"""Tests for Aggregates.

Run with: python -m pytest tests/test_aggregates.py -v
"""

from __future__ import annotations

import pytest
from app.domain.aggregates.stock_aggregate import (
    StockAggregate,
    InvalidStockCodeError,
    DuplicateSignalError,
)
from app.domain.aggregates.portfolio_aggregate import (
    PortfolioAggregate,
    PositionLimitExceededError,
    InsufficientCapitalError,
)
from app.domain.aggregates.trading_session_aggregate import (
    TradingSessionAggregate,
    OrderSide,
    OrderType,
    OrderStatus,
    InvalidOrderError,
    InvalidTransitionError,
)
from app.domain.repositories.stock import Stock, MarketData
from app.domain.repositories.signal import Signal, SignalType


class TestStockAggregate:
    """Tests for stock aggregate."""
    
    def test_create_stock(self):
        """Test creating stock aggregate."""
        stock = StockAggregate.create("600000", "Test Stock", "A")
        
        assert stock.code == "600000"
        assert stock.name == "Test Stock"
        assert stock.market == "A"
    
    def test_create_invalid_code(self):
        """Test invalid code."""
        with pytest.raises(InvalidStockCodeError):
            StockAggregate.create("", "Test")
    
    def test_add_market_data(self):
        """Test adding market data."""
        stock = StockAggregate.create("600000", "Test")
        
        data = MarketData(
            stock_code="600000",
            date="2024-01-01",
            open_price=10.0,
            high_price=11.0,
            low_price=9.5,
            close_price=10.5,
            volume=1000000
        )
        
        stock.add_market_data(data)
        
        assert stock.market_data_count == 1
        assert stock.latest_price == 10.5
    
    def test_add_market_data_wrong_code(self):
        """Test adding market data with wrong code."""
        stock = StockAggregate.create("600000", "Test")
        
        data = MarketData(
            stock_code="600001",
            date="2024-01-01",
            open_price=10.0,
            high_price=11.0,
            low_price=9.5,
            close_price=10.5,
            volume=1000000
        )
        
        with pytest.raises(Exception):
            stock.add_market_data(data)
    
    def test_add_signal(self):
        """Test adding signal."""
        stock = StockAggregate.create("600000", "Test")
        
        signal = Signal(
            stock_code="600000",
            signal_type=SignalType.BUY,
            source="test",
            confidence=0.8,
            reason="Test signal"
        )
        
        stock.add_signal(signal)
        
        assert stock.signal_count == 1
    
    def test_get_bullish_signals(self):
        """Test getting bullish signals."""
        stock = StockAggregate.create("600000", "Test")
        
        signal = Signal(
            stock_code="600000",
            signal_type=SignalType.BUY,
            source="test",
            confidence=0.8,
            reason="Test"
        )
        
        stock.add_signal(signal)
        
        bullish = stock.get_bullish_signals()
        
        assert len(bullish) == 1
    
    def test_get_consensus(self):
        """Test consensus."""
        stock = StockAggregate.create("600000", "Test")
        
        signal = Signal(
            stock_code="600000",
            signal_type=SignalType.BUY,
            source="test1",
            confidence=0.8,
            reason="Test"
        )
        
        stock.add_signal(signal)
        
        consensus = stock.get_consensus()
        
        assert consensus == SignalType.BUY
    
    def test_to_dict(self):
        """Test serialization."""
        stock = StockAggregate.create("600000", "Test")
        
        data = stock.to_dict()
        
        assert data["code"] == "600000"
        assert "id" in data


class TestPortfolioAggregate:
    """Tests for portfolio aggregate."""
    
    def test_create_portfolio(self):
        """Test creating portfolio."""
        portfolio = PortfolioAggregate.create(initial_cash=1000000)
        
        assert portfolio.cash == 1000000
        assert portfolio.position_count == 0
    
    def test_create_invalid_cash(self):
        """Test invalid cash."""
        with pytest.raises(InsufficientCapitalError):
            PortfolioAggregate.create(initial_cash=-100)
    
    def test_add_position(self):
        """Test adding position."""
        portfolio = PortfolioAggregate.create()
        
        portfolio.add_position("600000", 100, 10)
        
        assert portfolio.position_count == 1
        assert portfolio.cash < 1000000
    
    def test_add_position_insufficient_capital(self):
        """Test insufficient capital."""
        portfolio = PortfolioAggregate.create(initial_cash=100)
        
        with pytest.raises(InsufficientCapitalError):
            portfolio.add_position("600000", 100, 10)
    
    def test_reduce_position(self):
        """Test reducing position."""
        portfolio = PortfolioAggregate.create()
        portfolio.add_position("600000", 100, 10)
        
        proceeds = portfolio.reduce_position("600000", 50, 15)
        
        assert proceeds == 750
        assert portfolio.position_count == 1
    
    def test_close_position(self):
        """Test closing position."""
        portfolio = PortfolioAggregate.create()
        portfolio.add_position("600000", 100, 10)
        
        proceeds = portfolio.close_position("600000", 15)
        
        assert proceeds == 1500
        assert portfolio.position_count == 0
    
    def test_total_assets(self):
        """Test total assets."""
        portfolio = PortfolioAggregate.create(initial_cash=1000000)
        portfolio.add_position("600000", 100, 10)
        
        assert portfolio.total_assets == 1000000
    
    def test_to_dict(self):
        """Test serialization."""
        portfolio = PortfolioAggregate.create()
        
        data = portfolio.to_dict()
        
        assert "cash" in data
        assert "id" in data


class TestTradingSessionAggregate:
    """Tests for trading session aggregate."""
    
    def test_create_session(self):
        """Test creating session."""
        session = TradingSessionAggregate.create()
        
        assert session.order_count == 0
    
    def test_create_order(self):
        """Test creating order."""
        session = TradingSessionAggregate.create()
        
        session.create_order(
            "600000",
            OrderSide.BUY,
            OrderType.MARKET,
            100
        )
        
        assert session.order_count == 1
    
    def test_create_invalid_quantity(self):
        """Test invalid quantity."""
        session = TradingSessionAggregate.create()
        
        with pytest.raises(InvalidOrderError):
            session.create_order("600000", OrderSide.BUY, OrderType.MARKET, 0)
    
    def test_submit_order(self):
        """Test submitting order."""
        session = TradingSessionAggregate.create()
        
        session.create_order("600000", OrderSide.BUY, OrderType.MARKET, 100)
        session.submit_order("1")
        
        order = session.get_order("1")
        
        assert order.status == OrderStatus.SUBMITTED
    
    def test_fill_order(self):
        """Test filling order."""
        session = TradingSessionAggregate.create()
        
        session.create_order("600000", OrderSide.BUY, OrderType.MARKET, 100)
        session.submit_order("1")
        session.fill_order("1", 50, 10)
        
        order = session.get_order("1")
        
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == 50
    
    def test_cancel_order(self):
        """Test cancelling order."""
        session = TradingSessionAggregate.create()
        
        session.create_order("600000", OrderSide.BUY, OrderType.MARKET, 100)
        session.cancel_order("1")
        
        order = session.get_order("1")
        
        assert order.status == OrderStatus.CANCELLED
    
    def test_invalid_transition(self):
        """Test invalid transition."""
        session = TradingSessionAggregate.create()
        
        session.create_order("600000", OrderSide.BUY, OrderType.MARKET, 100)
        
        with pytest.raises(InvalidTransitionError):
            session.fill_order("1", 100, 10)
    
    def test_get_active_orders(self):
        """Test getting active orders."""
        session = TradingSessionAggregate.create()
        
        session.create_order("600000", OrderSide.BUY, OrderType.MARKET, 100)
        session.create_order("600001", OrderSide.SELL, OrderType.MARKET, 50)
        session.submit_order("1")
        
        active = session.get_active_orders()
        
        assert len(active) >= 1
    
    def test_to_dict(self):
        """Test serialization."""
        session = TradingSessionAggregate.create()
        
        session.create_order("600000", OrderSide.BUY, OrderType.MARKET, 100)
        
        data = session.to_dict()
        
        assert "order_count" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])