from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Intelligent data router - chooses optimal data source per operation."""


from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, is_dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.domain.ports.market_ports import HistoryPort, QuotePort, MarketDataProvider
from app.domain.ports.tdx_data_write_port import TdxDaykWritePort
from app.domain.ports.tdx_local_port import TdxLocalFilePort
from app.domain.entities import StockQuote

logger = get_logger(__name__)


class DataSourceType(Enum):
    TDX_FILE = "tdx_file"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    REDIS = "redis"
    AKSHARE = "akshare"


@dataclass
class DataQuery:
    """Data query specification."""
    symbol: str
    market: MarketCode
    start_date: str | None = None
    end_date: str | None = None
    fields: list[str] | None = None
    limit: int = 5000
    use_cache: bool = True


@dataclass
class DataSourceConfig:
    """Configuration for data sources."""
    tdx_root_path: str | None = None
    sqlite_path: str | None = None
    redis_config: dict | None = None

    enable_tdx: bool = True
    enable_mysql: bool = True
    enable_redis_cache: bool = True

    tdx_cache_size: int = 100
    redis_ttl: int = 3600


class DataSourceRouter:
    """Routes data operations to optimal source."""

    def __init__(
        self,
        config: DataSourceConfig,
        *,
        tdx_local_port: TdxLocalFilePort | None = None,
    ):
        self._config = config
        self._tdx_adapter: HistoryPort | None = None
        self._mysql_adapter: Any = None
        self._redis_cache: Any = None

        if self._config.enable_tdx and self._config.tdx_root_path:
            if tdx_local_port is not None:
                self._tdx_adapter = tdx_local_port.create_history_adapter(self._config.tdx_root_path)

    def _should_use_tdx(self, query: DataQuery) -> bool:
        """Decide if TDX file should be used."""
        if not self._config.enable_tdx:
            return False

        if self._tdx_adapter is None:
            return False

        if query.market != MarketCode.CN:
            return False

        return True

    def _should_use_mysql(self, query: DataQuery) -> bool:
        """Decide if MySQL should be used."""
        if not self._config.enable_mysql:
            return False
        return True

    def _should_use_cache(self, query: DataQuery) -> bool:
        """Decide if Redis cache should be used."""
        if not self._config.enable_redis_cache:
            return False
        return query.use_cache


class MarketDataService:
    """Unified market data service with intelligent routing."""

    def __init__(
        self,
        *,
        tdx_local_port: TdxLocalFilePort | None = None,
        dayk_write_port: TdxDaykWritePort | None = None,
        market_provider: MarketDataProvider | None = None,
        tdx_root_path: str | None = None,
    ) -> None:
        self._config = DataSourceConfig(tdx_root_path=tdx_root_path)
        self._router = DataSourceRouter(
            self._config, tdx_local_port=tdx_local_port,
        )

        if tdx_root_path:
            if tdx_local_port is not None:
                self._tdx = tdx_local_port.create_optimized_history(tdx_root_path, use_arrow=True)
            else:
                self._tdx = None
        else:
            self._tdx = None

        self._tdx_local_port = tdx_local_port
        self._dayk_write_port = dayk_write_port
        self._market_provider = market_provider

    def get_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
        prefer_source: DataSourceType = DataSourceType.MYSQL,
    ) -> list[dict[str, Any]]:
        """
        Get historical data - automatically chooses best source.

        A 股（与 TDX 入库一致）：MySQL 分表 → 本地 TDX lday。
        其他市场：沿用 TDX / MySQL 回退逻辑。
        """
        if market == MarketCode.CN:
            mysql_rows = self._query_mysql_history(symbol, market, start, end)
            if mysql_rows:
                return mysql_rows
            if prefer_source == DataSourceType.TDX_FILE and self._tdx:
                rows = self._tdx.get_stock_history(symbol, market, start, end)
                if rows:
                    return rows
            if self._tdx:
                return self._tdx.get_stock_history(symbol, market, start, end)
            return []

        if prefer_source == DataSourceType.TDX_FILE and self._tdx:
            rows = self._tdx.get_stock_history(symbol, market, start, end)
            if rows:
                return rows

        mysql_rows = self._query_mysql_history(symbol, market, start, end)
        if mysql_rows:
            return mysql_rows

        if self._tdx:
            return self._tdx.get_stock_history(symbol, market, start, end)

        return []

    def get_realtime_quote(self, symbol: str, market: MarketCode) -> GenericResponseDTO | None:
        """Get realtime quote: CN via CnRealtimeQuoteService, others via MarketDataProvider."""
        if market == MarketCode.CN:
            return self._get_cn_realtime_quote(symbol)

        return self._get_provider_realtime_quote(symbol, market)

    @staticmethod
    def _get_cn_realtime_quote(symbol: str) -> GenericResponseDTO | None:
        from app.modules.data.services.cn_realtime_quote_service import CnRealtimeQuoteService

        quote_map = CnRealtimeQuoteService().fetch_map([symbol])
        if not quote_map:
            return None

        candidates = [
            str(symbol or "").strip(),
            str(symbol or "").strip().lower(),
        ]
        try:
            candidates.append(SymbolNormalizer.normalize(symbol))
        except Exception as e:
            logger.warning("data_router_service.py._get_cn_realtime_quote: %s", e)
        try:
            candidates.append(SymbolNormalizer.to_db_code(symbol, market="CN"))
        except Exception as e:
            logger.warning("data_router_service.py._get_cn_realtime_quote: %s", e)

        for key in candidates:
            if key and key in quote_map:
                return quote_map[key]
        return next(iter(quote_map.values()), None)

    @staticmethod
    def _quote_entity_to_payload(q: object, *, fallback_symbol: str) -> GenericResponseDTO:
        if isinstance(q, dict):
            row = dict(q)
        elif isinstance(q, StockQuote):
            row = asdict(q)
        elif is_dataclass(q):
            row = asdict(q)
        else:
            row = {
                "code": getattr(q, "code", fallback_symbol) or fallback_symbol,
                "name": getattr(q, "name", "") or "",
                "price": float(getattr(q, "price", 0) or 0),
                "change_pct": float(getattr(q, "change_pct", 0) or 0),
                "volume": float(getattr(q, "volume", 0) or 0),
                "amount": float(getattr(q, "amount", 0) or 0),
            }
        code = str(row.get("code") or fallback_symbol)
        row["code"] = code.split(":", 1)[1] if ":" in code else code
        return row

    @classmethod
    def _get_provider_realtime_quote(cls, symbol: str, market: MarketCode) -> GenericResponseDTO | None:
        try:
            from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

            provider = get_market_data_provider()
        except RuntimeError:
            return None

        try:
            quotes = provider.get_realtime_quotes([symbol], market=market) or []
        except Exception as exc:
            logger.warning("provider realtime quote failed for %s (%s): %s", symbol, market, exc)
            return None

        if not quotes:
            return None
        return cls._quote_entity_to_payload(quotes[0], fallback_symbol=symbol)

    def write_backtest_result(self, symbol: str, data: list[dict]) -> bool:
        """Write operations always go to MySQL via TdxDaykWritePort."""
        return self._persist_to_mysql(symbol, data)

    def batch_preload(self, symbols: list[str], market: MarketCode = MarketCode.CN) -> int:
        """Preload symbols for fast access - TDX only."""
        if not self._tdx:
            return 0
        return self._tdx.preload_symbols(symbols, market)

    def _query_mysql_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        repo = get_tdx_dayk_write_port()
        if repo is None or market != MarketCode.CN:
            return []

        code = SymbolNormalizer.to_db_code(symbol, market="CN")
        if not (
            code.startswith("sh")
            or code.startswith("sz")
            or code.startswith("bj")
        ):
            return []

        start_d = (start or "")[:10] or None
        end_d = (end or "")[:10] or None
        rows = repo.fetch_history_rows_for_code(code, start_date=start_d, end_date=end_d)
        out: list[dict[str, Any]] = []
        for row in rows:
            date_str = str(row.get("date") or "")[:10]
            if not date_str:
                continue
            out.append(
                {
                    "date": date_str,
                    "open": float(row.get("open") or 0),
                    "high": float(row.get("high") or 0),
                    "low": float(row.get("low") or 0),
                    "close": float(row.get("close") or 0),
                    "volume": float(row.get("volume") or 0),
                    "amount": float(row.get("amount") or 0),
                }
            )
        return out

    def _persist_to_mysql(self, symbol: str, data: list[dict]) -> bool:
        if not data:
            return True

        repo = get_tdx_dayk_write_port()
        if repo is None:
            return False

        session = repo.open_sync_session()
        try:
            session.write_bars(symbol, data)
            session.commit()
            return True
        except Exception as exc:
            logger.warning("persist mysql history failed for %s: %s", symbol, exc)
            return False
        finally:
            session.close()


class ReadWriteSplitDataService:
    """Service with read-write splitting for maximum performance."""

    def __init__(self, tdx_root_path: str | None = None) -> None:
        self._read_service = MarketDataService(tdx_root_path=tdx_root_path)
        self._write_service = MarketDataService()

        self._tdx = self._read_service._tdx

    def read_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """Read from fastest available source (TDX > cache > MySQL)."""
        return self._read_service.get_history(symbol, market, start, end)

    def write_history(
        self,
        symbol: str,
        data: list[dict],
    ) -> bool:
        """Write always goes to MySQL."""
        return self._write_service.write_backtest_result(symbol, data)

    def batch_preload(self, symbols: list[str], market: MarketCode = MarketCode.CN) -> int:
        """Preload for fast batch reading."""
        if self._tdx:
            return self._tdx.preload_symbols(symbols, market)
        return 0