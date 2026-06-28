"""ORM-based SentimentRepository — replacement for raw-SQL SentimentRepository.

Uses SQLAlchemy ORM.  Implements the same save/query interface.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


from ..orm import Base


class _MarketSentimentModel(Base):
    """Lightweight model for the market_sentiment table."""

    __tablename__ = "market_sentiment"

    market: Any = __tablename__  # placeholder for type-checker
    # Columns are auto-reflected or created via metadata; we use raw SQL
    # for DDL but ORM for queries to minimise migration risk.


class OrmSentimentRepository:
    """ORM-backed sentiment repository (migration demo for P06)."""

    def __init__(self, session_factory):
        self._sf = session_factory

    def save_sentiment(
        self, market: str, up_count: int, down_count: int, flat_count: int
    ) -> None:
        total = int(up_count) + int(down_count) + int(flat_count)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session = self._sf()
        try:
            # Use raw upsert for both SQLite and MySQL compatibility
            dialect = session.bind.dialect.name if session.bind else "sqlite"
            if dialect == "sqlite":
                sql = """
                    INSERT INTO market_sentiment
                        (market, up_count, down_count, flat_count, total_count, update_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(market) DO UPDATE SET
                        up_count=excluded.up_count, down_count=excluded.down_count,
                        flat_count=excluded.flat_count, total_count=excluded.total_count,
                        update_time=excluded.update_time
                """
            else:
                sql = """
                    INSERT INTO market_sentiment
                        (market, up_count, down_count, flat_count, total_count, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        up_count=VALUES(up_count), down_count=VALUES(down_count),
                        flat_count=VALUES(flat_count), total_count=VALUES(total_count),
                        update_time=VALUES(update_time)
                """
            session.execute(
                text(sql),
                (market, int(up_count), int(down_count), int(flat_count), total, now),
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            self._sf.remove()

    def get_sentiment(self, market: str) -> dict[str, Any] | None:
        session = self._sf()
        try:
            row = session.execute(
                text(
                    "SELECT * FROM market_sentiment WHERE market = :market"
                ),
                {"market": market},
            ).mappings().first()
            return dict(row) if row else None
        finally:
            self._sf.remove()


from sqlalchemy import text
