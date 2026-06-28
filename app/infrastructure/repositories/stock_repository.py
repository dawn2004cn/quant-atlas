from __future__ import annotations
"""Stock Repository - MySQL Implementation.

Implements IStockRepository using SQLAlchemy.
"""



from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.base import Entity
from app.domain.repositories.stock import IStockRepository, MarketData, IMarketDataRepository
from app.domain.repositories.stock import Stock as StockEntity


from app.core.logger import get_logger

logger = get_logger(__name__)


class MySQLStockRepository(IStockRepository):
    """MySQL implementation of stock repository."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def _get_session(self) -> Session:
        return self._session_factory()

    def get_by_code(self, code: str) -> StockEntity | None:
        """Get stock by code."""
        with self._get_session() as session:
            from app.infrastructure.database.models.market import Stock
            stmt = select(Stock).where(Stock.code == code)
            result = session.execute(stmt).scalar_one_or_none()
            if result:
                return StockEntity(
                    code=result.code,
                    name=result.name,
                    market="A",
                    id=Entity.parse_uuid(result.code) if hasattr(Entity, 'parse_uuid') else None
                )
            return None

    def list_by_market(self, market: str = "A", limit: int = 100) -> list[StockEntity]:
        """List stocks by market."""
        with self._get_session() as session:
            from app.infrastructure.database.models.market import Stock
            stmt = select(Stock).limit(limit)
            results = session.execute(stmt).scalars().all()
            return [
                StockEntity(code=r.code, name=r.name, market=market)
                for r in results
            ]

    def search(self, query: str, limit: int = 20) -> list[StockEntity]:
        """Search stocks by name or code."""
        with self._get_session() as session:
            from app.infrastructure.database.models.market import Stock
            stmt = (
                select(Stock)
                .where(
                    (Stock.code.ilike(f"%{query}%")) |
                    (Stock.name.ilike(f"%{query}%"))
                )
                .limit(limit)
            )
            results = session.execute(stmt).scalars().all()
            return [
                StockEntity(code=r.code, name=r.name, market="A")
                for r in results
            ]


class MySQLMarketDataRepository(IMarketDataRepository):
    """MySQL implementation of market data repository."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def _get_session(self) -> Session:
        return self._session_factory()

    def get_daily(self, code: str, start_date: str, end_date: str) -> list[MarketData]:
        """Get daily market data."""
        with self._get_session() as session:
            from app.infrastructure.database.models.market import StockHistory
            stmt = (
                select(StockHistory)
                .where(StockHistory.stock_code == code)
                .where(StockHistory.date >= start_date)
                .where(StockHistory.date <= end_date)
                .order_by(StockHistory.date)
            )
            results = session.execute(stmt).scalars().all()
            return [
                MarketData(
                    stock_code=r.stock_code,
                    date=r.date,
                    open_price=r.open,
                    high_price=r.high,
                    low_price=r.low,
                    close_price=r.close,
                    volume=int(r.volume),
                )
                for r in results
            ]

    def get_latest(self, code: str) -> MarketData | None:
        """Get latest market data."""
        with self._get_session() as session:
            from app.infrastructure.database.models.market import StockHistory
            stmt = (
                select(StockHistory)
                .where(StockHistory.stock_code == code)
                .order_by(StockHistory.date.desc())
                .limit(1)
            )
            result = session.execute(stmt).scalar_one_or_none()
            if result:
                return MarketData(
                    stock_code=result.stock_code,
                    date=result.date,
                    open_price=result.open,
                    high_price=result.high,
                    low_price=result.low,
                    close_price=result.close,
                    volume=int(result.volume),
                )
            return None


__all__ = ["MySQLStockRepository", "MySQLMarketDataRepository"]
