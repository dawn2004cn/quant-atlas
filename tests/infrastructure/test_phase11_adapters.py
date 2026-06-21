"""Tests for Phase 11: Infrastructure Adapters (Mappers & Repositories)."""

import unittest
from datetime import datetime

from app.infrastructure.persistence.mappers import (
    StockMapper,
    QuoteMapper,
    UserMapper,
    WatchlistMapper,
    PositionMapper,
    SignalMapper,
    MapperRegistry,
)
from app.infrastructure.repositories.domain_repositories import (
    StockRepository,
    QuoteRepository,
    WatchlistRepository,
    PositionRepository,
    SignalRepository,
)


class TestMappers(unittest.TestCase):
    """Test entity mappers."""

    def test_stock_mapper_to_entity(self):
        """Test StockMapper to_entity."""
        db_model = {
            "code": "600519",
            "name": "贵州茅台",
            "market": "CN",
            "industry": "白酒",
            "sector": "消费",
        }

        entity = StockMapper.to_entity(db_model)

        self.assertEqual(entity["code"], "600519")
        self.assertEqual(entity["name"], "贵州茅台")
        self.assertEqual(entity["market"], "CN")

    def test_stock_mapper_to_db_model(self):
        """Test StockMapper to_db_model."""
        entity = {
            "code": "600519",
            "name": "贵州茅台",
            "market": "CN",
            "industry": "白酒",
        }

        db_model = StockMapper.to_db_model(entity)

        self.assertEqual(db_model["code"], "600519")
        self.assertIn("created_at", db_model)

    def test_quote_mapper(self):
        """Test QuoteMapper."""
        db_model = {
            "code": "600519",
            "price": 1800.0,
            "change": 10.0,
            "change_pct": 0.56,
            "volume": 1000000,
        }

        entity = QuoteMapper.to_entity(db_model)

        self.assertEqual(entity["price"], 1800.0)
        self.assertEqual(entity["change_pct"], 0.56)

    def test_user_mapper(self):
        """Test UserMapper."""
        db_model = {
            "id": "123",
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
        }

        entity = UserMapper.to_entity(db_model)

        self.assertEqual(entity["username"], "testuser")
        self.assertTrue(entity["is_active"])

    def test_position_mapper(self):
        """Test PositionMapper."""
        entity = {
            "user_id": "user1",
            "code": "600519",
            "name": "贵州茅台",
            "quantity": 100,
            "avg_cost": 1700.0,
            "side": "long",
        }

        db_model = PositionMapper.to_db_model(entity)

        self.assertEqual(db_model["quantity"], 100)
        self.assertEqual(db_model["side"], "long")

    def test_signal_mapper(self):
        """Test SignalMapper."""
        entity = {
            "code": "600519",
            "signal_type": "breakout",
            "strength": "strong",
            "price": 1800.0,
            "confidence": 75.0,
        }

        db_model = SignalMapper.to_db_model(entity)

        self.assertEqual(db_model["signal_type"], "breakout")
        self.assertEqual(db_model["confidence"], 75.0)

    def test_mapper_registry(self):
        """Test MapperRegistry."""
        mapper = MapperRegistry.get_mapper("stock")
        self.assertIsInstance(mapper, StockMapper)

        mapper = MapperRegistry.get_mapper("quote")
        self.assertIsInstance(mapper, QuoteMapper)

        mapper = MapperRegistry.get_mapper("unknown")
        self.assertIsNone(mapper)


class TestRepositories(unittest.TestCase):
    """Test repositories."""

    def setUp(self):
        """Set up test repositories."""
        self.stock_repo = StockRepository()
        self.quote_repo = QuoteRepository()
        self.watchlist_repo = WatchlistRepository()
        self.position_repo = PositionRepository()
        self.signal_repo = SignalRepository()

    def test_stock_repository(self):
        """Test StockRepository."""
        stock = {
            "code": "600519",
            "name": "贵州茅台",
            "market": "CN",
            "industry": "白酒",
        }

        created = self.stock_repo.create(stock)
        self.assertIn("id", created)

        retrieved = self.stock_repo.get_by_id(created["id"])
        self.assertIsNotNone(retrieved)

        by_code = self.stock_repo.find_by_code("600519")
        self.assertIsNotNone(by_code)

    def test_quote_repository(self):
        """Test QuoteRepository."""
        quote = {
            "code": "600519",
            "price": 1800.0,
            "change": 10.0,
        }

        self.quote_repo.create(quote)

        retrieved = self.quote_repo.find_by_code("600519")
        self.assertEqual(retrieved["price"], 1800.0)

    def test_watchlist_repository(self):
        """Test WatchlistRepository."""
        watchlist = {
            "user_id": "user1",
            "name": "My Watchlist",
            "is_default": True,
        }

        self.watchlist_repo.create(watchlist)

        by_user = self.watchlist_repo.find_by_user("user1")
        self.assertEqual(len(by_user), 1)

        default = self.watchlist_repo.find_default("user1")
        self.assertIsNotNone(default)

    def test_position_repository(self):
        """Test PositionRepository."""
        position = {
            "user_id": "user1",
            "code": "600519",
            "quantity": 100,
            "status": "open",
        }

        self.position_repo.create(position)

        open_positions = self.position_repo.find_open_positions("user1")
        self.assertEqual(len(open_positions), 1)

    def test_signal_repository(self):
        """Test SignalRepository."""
        signal = {
            "code": "600519",
            "signal_type": "breakout",
            "strength": "strong",
        }

        self.signal_repo.create(signal)

        by_code = self.signal_repo.find_by_code("600519")
        self.assertEqual(len(by_code), 1)


class TestValidators(unittest.TestCase):
    """Test DTO validators."""

    def test_stock_code_validator(self):
        """Test StockCodeValidator."""
        from app.application.dto.validators import StockCodeValidator

        self.assertTrue(StockCodeValidator.validate("600519"))
        self.assertTrue(StockCodeValidator.validate("sh600519"))
        self.assertFalse(StockCodeValidator.validate("abc"))
        self.assertFalse(StockCodeValidator.validate(""))

        self.assertEqual(StockCodeValidator.normalize("sh600519"), "600519")

    def test_price_validator(self):
        """Test PriceValidator."""
        from app.application.dto.validators import PriceValidator

        self.assertTrue(PriceValidator.validate(1800.0))
        self.assertFalse(PriceValidator.validate(0))
        self.assertFalse(PriceValidator.validate(-100))
        self.assertFalse(PriceValidator.validate(2000000))

    def test_stock_request_dto(self):
        """Test StockRequestDTO."""
        from app.application.dto.validators import StockRequestDTO

        dto = StockRequestDTO(code="600519", name="贵州茅台")
        self.assertEqual(dto.code, "600519")

        dto = StockRequestDTO(code="sh600519", name="贵州茅台")
        self.assertEqual(dto.code, "600519")

    def test_trade_request_dto(self):
        """Test TradeRequestDTO."""
        from app.application.dto.validators import TradeRequestDTO

        dto = TradeRequestDTO(
            code="600519",
            side="buy",
            quantity=100,
            price=1800.0
        )
        self.assertEqual(dto.side, "buy")

    def test_backtest_request_dto(self):
        """Test BacktestRequestDTO."""
        from app.application.dto.validators import BacktestRequestDTO

        dto = BacktestRequestDTO(
            codes=["600519", "000001"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=100000.0
        )
        self.assertEqual(len(dto.codes), 2)


if __name__ == "__main__":
    unittest.main()