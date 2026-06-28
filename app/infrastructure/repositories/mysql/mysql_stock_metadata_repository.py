from __future__ import annotations

"""MySQL ``base_stock_reference`` metadata repository."""

from typing import Any

from sqlalchemy import text

from app.domain.ports.stock_metadata_port import StockMetadataRepository
from app.infrastructure.database.db_manager import get_session
from app.infrastructure.database.mysql_settings import MysqlSettings
from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer


class MySQLStockMetadataRepository(StockMetadataRepository):
    def __init__(self, mysql: MysqlSettings) -> None:
        self._mysql = mysql

    def get_basic_info(self, code: str) -> dict[str, Any]:
        clean_code = SymbolNormalizer.normalize_code(code).zfill(6)
        session = get_session(self._mysql)
        try:
            row = session.execute(
                text(
                    "SELECT name, industry, region, pb, holder_count "
                    "FROM base_stock_reference WHERE code = :code"
                ),
                {"code": clean_code},
            ).fetchone()
            if not row:
                return {}
            return {
                "name": row[0],
                "industry": row[1] or "",
                "region": row[2],
                "pb": row[3],
                "holder_count": row[4],
            }
        finally:
            session.close()

    def get_batch(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        if not codes:
            return {}
        unique_codes = list({SymbolNormalizer.normalize_code(str(c)).zfill(6) for c in codes})
        session = get_session(self._mysql)
        try:
            rows = session.execute(
                text(
                    "SELECT code, name, industry, region "
                    "FROM base_stock_reference WHERE code IN :codes"
                ),
                {"codes": tuple(unique_codes)},
            ).fetchall()
            result: dict[str, dict[str, Any]] = {}
            for row in rows:
                result[str(row[0]).zfill(6)] = {
                    "name": row[1],
                    "industry": row[2] or "",
                    "region": row[3],
                }
            return result
        finally:
            session.close()

    def enrich_stock_list(self, stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not stocks:
            return stocks
        codes = [SymbolNormalizer.normalize_code(str(s.get("code", ""))).zfill(6) for s in stocks]
        meta = self.get_batch(codes)
        for stock in stocks:
            code = SymbolNormalizer.normalize_code(str(stock.get("code", ""))).zfill(6)
            if code in meta:
                stock.update(meta[code])
        return stocks


class NullStockMetadataRepository(StockMetadataRepository):
    """Fallback when MySQL reference table is unavailable."""

    def get_basic_info(self, code: str) -> dict[str, Any]:
        return {}

    def get_batch(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        return {}

    def enrich_stock_list(self, stocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return stocks
