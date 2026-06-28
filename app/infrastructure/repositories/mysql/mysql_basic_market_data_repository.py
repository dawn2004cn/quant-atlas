"""MySQL implementation for BasicMarketDataRepository — thin facade.

Delegates read methods to MySQLBasicMarketDataReadRepository and write
methods to MySQLBasicMarketDataWriteRepository.
"""

from datetime import datetime, timezone
from typing import Any

from app.infrastructure.repositories.factory import RepositoryType, register_repo

from .mysql_basic_market_data_read_repository import MySQLBasicMarketDataReadRepository
from .mysql_basic_market_data_write_repository import MySQLBasicMarketDataWriteRepository

import logging

logger = logging.getLogger(__name__)


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


@register_repo(RepositoryType.MYSQL, "basic_market_data")
class MySQLBasicMarketDataRepository:
    """MySQL implementation of Basic Market Data Repository (facade).

    Read operations are delegated to ``_read`` and write operations to ``_write``.
    """

    def __init__(self, mysql=None, session_factory=None) -> None:
        self._mysql = mysql
        self._session_factory = session_factory
        self._read = MySQLBasicMarketDataReadRepository(mysql=mysql, session_factory=session_factory)
        self._write = MySQLBasicMarketDataWriteRepository(mysql=mysql, session_factory=session_factory)

    # ------------------------------------------------------------------
    # Longhu — delegation
    # ------------------------------------------------------------------

    def replace_longhu_day(self, trade_date: str, rows: list[dict[str, Any]]) -> int:
        return self._write.replace_longhu_day(trade_date, rows)

    def upsert_longhu_rows(self, rows: list[dict[str, Any]]) -> int:
        return self._write.upsert_longhu_rows(rows)

    def list_longhu_by_date(self, trade_date: str, *, limit: int = 500) -> list[dict[str, Any]]:
        return self._read.list_longhu_by_date(trade_date, limit=limit)

    def list_longhu_latest_dates(self, limit: int = 20) -> list[str]:
        return self._read.list_longhu_latest_dates(limit=limit)

    def list_longhu_for_code(self, code: str, *, limit: int = 20) -> list[dict[str, Any]]:
        return self._read.list_longhu_for_code(code, limit=limit)

    def count_longhu_rows(self) -> int:
        return self._read.count_longhu_rows()

    def latest_longhu_trade_date(self) -> str | None:
        return self._read.latest_longhu_trade_date()

    # ------------------------------------------------------------------
    # Meta — delegation
    # ------------------------------------------------------------------

    def set_meta(self, key: str, value: str) -> None:
        self._write.set_meta(key, value)

    def get_meta(self, key: str) -> str | None:
        return self._read.get_meta(key)

    # ------------------------------------------------------------------
    # Financial stash — delegation
    # ------------------------------------------------------------------

    def upsert_financial_stash(self, code: str, payload: dict[str, Any]) -> None:
        self._write.upsert_financial_stash(code, payload)

    def count_financial_stash_rows(self) -> int:
        return self._read.count_financial_stash_rows()

    # ------------------------------------------------------------------
    # Yanbao — delegation
    # ------------------------------------------------------------------

    def insert_yanbao_batch(self, category: str, items: list[dict[str, Any]], batch_id: str) -> int:
        return self._write.insert_yanbao_batch(category, items, batch_id)

    def list_yanbao(self, *, category: str | None = None, limit: int = 120) -> list[dict[str, Any]]:
        return self._read.list_yanbao(category=category, limit=limit)
